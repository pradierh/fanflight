import os
from datetime import datetime, timedelta
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json
from collections import defaultdict
import pandas as pd
from pathlib import Path

# --- ML / inference ---
import mlflow
import numpy as np
import xgboost as xgb
from mlflow.tracking import MlflowClient
from feature_builder import (
    FEATURE_COLS,load_mappings, build_features_for_flight, features_to_vector,
)

# -- Monitoring
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="API de Vols - Coupe du Monde 2026")
Instrumentator().instrument(app).expose(app) #Exposition des métriques pour monitoring

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Autorise front Next.js
    allow_credentials=True,
    allow_methods=["*"], # Autorise tous les verbes (GET, POST, etc.)
    allow_headers=["*"], # Autorise tous les headers
)

API_KEY = os.getenv("API_KEY_SERAPI")

# ------------------------------------------------------------------
# Configuration ML
# ------------------------------------------------------------------
MLFLOW_URI    = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
DATA_DIR      = Path(os.getenv("DATA_DIR", "/opt/data"))
MAPPINGS_PATH = DATA_DIR / "category_mappings.json"

# ------------------------------------------------------------------
# Configuration météo (prévision Open-Meteo)
# ------------------------------------------------------------------
FORECAST_URL         = "https://api.open-meteo.com/v1/forecast"
FORECAST_HOURLY      = "temperature_2m,precipitation,weather_code,wind_speed_10m,visibility,snowfall"
FORECAST_WINDOW_DAYS = 16

# Variables globales chargées au démarrage
MODEL      = None
MAPPINGS   = None
MODEL_NAME = None

# ==================================================================
# DB
# ==================================================================

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
        cursor_factory=RealDictCursor
    )

# ==================================================================
# HEALTH / READY
# ==================================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_name": MODEL_NAME,
        "mappings_loaded": MAPPINGS is not None,
    }


@app.get("/ready")
def ready():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS ok;")
        cursor.fetchone()
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database is not ready: {e}",
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ==================================================================
# CHARGEMENT DU MODELE AU DÉMARRAGE
# ==================================================================

@app.on_event("startup")
def load_model():
    global MODEL, MAPPINGS, MODEL_NAME

    mlflow.set_tracking_uri(MLFLOW_URI)

    # Mappings d'encodage
    try:
        MAPPINGS = load_mappings(MAPPINGS_PATH)
        print(f"[ML] Mappings chargés depuis {MAPPINGS_PATH}")
    except Exception as e:
        print(f"[ML] Mappings introuvables ({e}) - prédictions désactivées.")
        MAPPINGS = None

    # Chargement du booster XGBoost
    try:
        client = MlflowClient()
        versions = client.get_latest_versions("flight_delay_xgboost")
        if not versions:
            raise Exception("Aucune version de flight_delay_xgboost")
        latest = max(versions, key=lambda v: int(v.version))
        run_id = latest.run_id
        local_path = client.download_artifacts(run_id, "model/model.xgb")
        print(f"[ML] Artefact téléchargé : {local_path}")
        booster = xgb.Booster()
        booster.load_model(local_path)
        MODEL = booster
        MODEL_NAME = "xgboost"
        print(f"[ML] Booster XGBoost chargé (version {latest.version})")
    except Exception as e:
        print(f"[ML] Échec chargement XGBoost : {e}")
        print("[ML] API démarre sans modèle - les vols seront retournés sans score de retard.")


# ==================================================================
# MÉTÉO POUR L'INFÉRENCE
# ==================================================================

def get_airport_coords(cursor, iata_code):
    """Coordonnées d'un aéroport depuis DIM_AIRPORT."""
    cursor.execute(
        "SELECT latitude, longitude FROM dim_airport WHERE iata_code = %s",
        (iata_code,)
    )
    row = cursor.fetchone()
    if row and row["latitude"] is not None:
        return float(row["latitude"]), float(row["longitude"])
    return None


def fetch_forecast_weather(lat, lon, target_dt):
    """
    Récupère la prévision météo réelle pour une date/heure de vol proche.
    Retourne un dict météo ou None si indisponible.
    """
    date_str = target_dt.strftime("%Y-%m-%d")
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date_str,
        "end_date": date_str,
        "hourly": FORECAST_HOURLY,
        "timezone": "auto",
    }
    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        times = hourly.get("time", [])
        target_hour = target_dt.hour
        for i, t in enumerate(times):
            hour = int(t.split("T")[1][:2]) if "T" in t else int(t.split(" ")[1][:2])
            if hour == target_hour:
                return {
                    "temperature_c":    hourly.get("temperature_2m", [None])[i],
                    "precipitation_mm": hourly.get("precipitation", [None])[i],
                    "weather_code":     hourly.get("weather_code", [None])[i],
                    "wind_speed_kmh":   hourly.get("wind_speed_10m", [None])[i],
                    "visibility_m":     hourly.get("visibility", [None])[i],
                    "snowfall_cm":      hourly.get("snowfall", [None])[i],
                }
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ML] Prévision météo indisponible : {e}")
        return None


def get_weather_for_inference(cursor, flight):
    """
    Récupère la météo d'un vol pour la prédiction, avec stratégie en cascade :
    1) Vol dans la fenêtre de prévision (<= 16 jours) -> prévision réelle Open-Meteo.
    2) Sinon, repli sur FACT_FLIGHT_WEATHER (approximation saisonnière N-1).
    3) Sinon, valeurs par défaut gérées par build_features_for_flight.
    """
    dep_time = flight.get("departure_airport_time")
    if isinstance(dep_time, str):
        dep_time = datetime.fromisoformat(dep_time)

    if dep_time is not None:
        now = datetime.now(dep_time.tzinfo) if dep_time.tzinfo else datetime.now()
        days_ahead = (dep_time - now).days

        if 0 <= days_ahead <= FORECAST_WINDOW_DAYS:
            # On utilise arrival_airport_code (nom de colonne de notre schéma)
            coords = get_airport_coords(cursor, flight.get("arrival_airport_code"))
            if coords:
                forecast = fetch_forecast_weather(coords[0], coords[1], dep_time)
                if forecast and forecast.get("temperature_c") is not None:
                    return forecast

    cursor.execute(
        """
        SELECT temperature_c, precipitation_mm, weather_code,
               wind_speed_kmh, visibility_m, snowfall_cm
        FROM fact_flight_weather
        WHERE flight_sk = %s
        """,
        (flight["flight_sk"],),
    )
    row = cursor.fetchone()
    if row:
        return dict(row)

    return None


def clean_unused_cols(flights):
    """Supprime les champs internes non destinés à l'API publique."""
    for flight in flights:
        flight.pop("is_delayed", None)
    return flights


def predict_delay(cursor, flights):
    """
    Ajoute delay_probability et delay_prediction à chaque vol.
    Si le modèle n'est pas chargé, met les champs à None sans planter.
    """
    if MODEL is None or MAPPINGS is None:
        for f in flights:
            f["delay_probability"] = None
            f["delay_prediction"]  = None
            f["model_used"]        = None
        return flights

    for f in flights:
        try:
            segment_probs = []
            
            for segment in f["segments"]:
                flight_for_ml = {
                    **segment,
                    "price":                  f.get("price"),
                    "is_best":                f.get("is_best"),
                    "total_journey_duration": f.get("total_duration"),
                    "layover_duration":       segment.get("layover_duration") or 0,
                }

                weather = get_weather_for_inference(cursor, flight_for_ml)
                feats   = build_features_for_flight(flight_for_ml, weather, MAPPINGS)
                X       = np.array([features_to_vector(feats)], dtype=np.float32)
                X_df    = pd.DataFrame(X, columns=FEATURE_COLS)
                dmatrix = xgb.DMatrix(X_df)
                prob    = float(MODEL.predict(dmatrix)[0])
                segment_probs.append(max(0.0, min(1.0, prob)))

            # Probabilité globale = pire segment
            worst_prob = max(segment_probs)
            f["delay_probability"] = round(worst_prob, 4)
            f["delay_prediction"]  = bool(worst_prob >= 0.5)
            f["model_used"]        = MODEL_NAME

        except Exception as e:
            print(f"[ML] Erreur prédiction : {e}")
            f["delay_probability"] = None
            f["delay_prediction"]  = None
            f["model_used"]        = MODEL_NAME

    return flights


# ==================================================================
# LOGIQUE VOLS
# ==================================================================

def check_flight_db(cursor, departure_city, arrival_city, match_date_exact):
    flights_query = """
    WITH CTE_DEPARTURE_FLIGHT as(
        select journey_sk
        from FACT_FLIGHT f
        JOIN DIM_AIRPORT dep_a ON f.departure_airport_code = dep_a.iata_code
        JOIN DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
        WHERE LOWER(dep_c.city) = LOWER(%s) and f.pos = 0
    )
    , CTE_ARRIVAL_FLIGHT as (
        select journey_sk
        from fact_flight f
        JOIN DIM_AIRPORT arr_a ON f.arrival_airport_code = arr_a.iata_code
        JOIN DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
        WHERE LOWER(arr_c.city) = LOWER(%s)
        AND f.pos = (
            SELECT MAX(pos) FROM fact_flight f2
            WHERE f2.journey_sk = f.journey_sk
        )
        AND f.arrival_airport_time BETWEEN (%s::date - INTERVAL '3 days') AND (%s - INTERVAL '5 hours')
    )
    , UNIONED as (
        select df.journey_sk
        from CTE_DEPARTURE_FLIGHT df
        join CTE_ARRIVAL_FLIGHT af on df.journey_sk = af.journey_sk
    )
    SELECT
        f.flight_sk,
        f.journey_sk,
        dep_c.city as departure_city,
        f.departure_airport_code,
        f.departure_airport_time,
        arr_c.city as arrival_city,
        f.arrival_airport_code,
        f.arrival_airport_time,
        f.duration,
        f.layover_duration,
        f.total_journey_duration,
        f.price,
        f.flight_number,
        f.airline,
        f.is_best,
        f.pos
    FROM FACT_FLIGHT f
    join UNIONED u on f.journey_sk = u.journey_sk
    JOIN DIM_AIRPORT dep_a ON f.departure_airport_code = dep_a.iata_code
    JOIN DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
    JOIN DIM_AIRPORT arr_a ON f.arrival_airport_code = arr_a.iata_code
    JOIN DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
    ORDER BY journey_sk, departure_airport_time asc;
    """

    cursor.execute(flights_query, (departure_city, arrival_city, match_date_exact, match_date_exact))
    rows = cursor.fetchall()

    journeys = defaultdict(list)
    for row in rows:
        journeys[row['journey_sk']].append(dict(row))

    flights = []
    for journey_sk, segments in journeys.items():
        segments.sort(key=lambda x: x['pos'])
        first = segments[0]
        last  = segments[-1]

        flights.append({
            'journey_sk':             journey_sk,
            'price':                  first['price'],
            'airline':                first['airline'],
            'is_best':                first['is_best'],
            'total_duration':         first['total_journey_duration'],
            'departure_airport_code': first['departure_airport_code'],
            'departure_airport_time': str(first['departure_airport_time']),
            'departure_city':         first['departure_city'],
            'arrival_airport_code':   last['arrival_airport_code'],
            'arrival_airport_time':   str(last['arrival_airport_time']),
            'arrival_city':           last['arrival_city'],
            'nb_escales':             len(segments) - 1,
            'segments':               segments,
        })

    return flights


def get_flights_api(cursor, conn, departure_city, arrival_city, match_date_exact):
    cursor.execute("""
        SELECT iata_code FROM dim_airport a
        JOIN dim_city c ON a.id_city = c.id_city
        WHERE trim(lower(c.city)) = trim(lower(%s))
    """, (departure_city,))
    aeroports_depart = cursor.fetchall()

    cursor.execute("""
        SELECT iata_code FROM dim_airport a
        JOIN dim_city c ON a.id_city = c.id_city
        WHERE trim(lower(c.city)) = trim(lower(%s))
    """, (arrival_city,))
    aeroports_arrivee = cursor.fetchall()

    if not aeroports_depart or not aeroports_arrivee:
        raise HTTPException(
            status_code=400,
            detail="Impossible de trouver les codes aéroports (IATA) pour ces villes dans le dictionnaire."
        )

    all_flights_raw = []
    for aero_dep in aeroports_depart:
        code_iata_depart = aero_dep['iata_code']
        for aero_arr in aeroports_arrivee:
            code_iata_arrivee = aero_arr['iata_code']
            for day in range(2):
                date_vol = (match_date_exact - timedelta(days=day + 1)).date()
                params = {
                    "engine":        "google_flights",
                    "type":          "2",
                    "departure_id":  code_iata_depart,
                    "arrival_id":    code_iata_arrivee,
                    "outbound_date": date_vol,
                    "currency":      "EUR",
                    "hl":            "fr",
                    "api_key":       API_KEY
                }
                try:
                    response = requests.get("https://serpapi.com/search", params=params)
                    if response.status_code == 200:
                        all_flights_raw.append(response.json())
                except requests.exceptions.RequestException:
                    print(f"Erreur API pour {code_iata_depart} -> {code_iata_arrivee}")

    job_id = insert_raw_flights(cursor, conn, all_flights_raw)
    return job_id


def insert_raw_flights(cursor, conn, raw_flight):
    query = "INSERT INTO flights_raw (json_data) VALUES (%s) RETURNING id;"
    cursor.execute(query, (json.dumps(raw_flight),))
    job_id = cursor.fetchone()['id']
    cursor.execute("SELECT pg_notify('new_flight', %s)", (str(job_id),))
    conn.commit()
    return job_id


def wait_to_spark(cursor, job_id):
    start   = time.time()
    timeout = 120
    while True:
        if time.time() - start > timeout:
            raise Exception("Timeout")
        cursor.execute(
            "SELECT bool_and(processed) as is_done FROM flights_raw WHERE id = ANY(%s)",
            ([job_id],)   # fix : liste, pas scalaire
        )
        row = cursor.fetchone()
        if row and row['is_done'] == True:
            return True
        time.sleep(2)


def enrich_airports(cursor, conn):
    cursor.execute("""
        SELECT DISTINCT f.departure_airport_code as iata_code
        FROM FACT_FLIGHT f
        WHERE NOT EXISTS (
            SELECT 1 FROM DIM_AIRPORT a
            WHERE a.iata_code = f.departure_airport_code
        )
        UNION
        SELECT DISTINCT f.arrival_airport_code as iata_code
        FROM FACT_FLIGHT f
        WHERE NOT EXISTS (
            SELECT 1 FROM DIM_AIRPORT a
            WHERE a.iata_code = f.arrival_airport_code
        )
    """)

    rows         = cursor.fetchall()
    unknown_iata = [row['iata_code'] for row in rows]

    if not unknown_iata:
        return

    airports_csv = pd.read_csv('/opt/data/raw_data/airport-codes.csv')

    for iata in unknown_iata:
        result = airports_csv[airports_csv['iata_code'] == iata]

        if not result.empty:
            row     = result.iloc[0]
            city    = str(row['municipality']).strip().title()
            country = str(row['iso_country']).strip().upper()
            name    = str(row['name']).strip().lower()
        else:
            city, country, name = 'Unknown', 'Unknown', iata

        cursor.execute("""
            INSERT INTO DIM_CITY (CITY, COUNTRY, IS_HOST_CITY)
            VALUES (%s, %s, FALSE)
            ON CONFLICT (CITY) DO NOTHING
        """, (city, country))

        cursor.execute("SELECT ID_CITY FROM DIM_CITY WHERE CITY = %s", (city,))
        id_city = cursor.fetchone()['id_city']

        cursor.execute("""
            INSERT INTO DIM_AIRPORT (IATA_CODE, NAME, ID_CITY)
            VALUES (%s, %s, %s)
            ON CONFLICT (IATA_CODE) DO NOTHING
        """, (iata, name, id_city))

        conn.commit()


# ==================================================================
# ENDPOINTS
# ==================================================================

@app.get("/api/flights/{match_id}")
def get_flights(match_id: int, departure_city: str):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        match_query = """
            SELECT m.MATCH_DATE, c.CITY as arrival_city
            FROM FACT_MATCHS m
            JOIN DIM_CITY c ON m.ID_CITY = c.ID_CITY
            WHERE m.MATCH_ID = %s
        """
        cursor.execute(match_query, (match_id,))
        match_info = cursor.fetchone()

        if not match_info:
            raise HTTPException(status_code=404, detail=f"Match {match_id} introuvable.")

        match_date_exact = match_info['match_date']
        arrival_city     = match_info['arrival_city']

        print(departure_city)
        print(arrival_city)

        flights = check_flight_db(cursor, departure_city, arrival_city, match_date_exact)

        if flights:
            flights = predict_delay(cursor, flights)
            cursor.close()
            conn.close()
            return {
                "meta": {
                    "match_id":          match_id,
                    "destination_city":  arrival_city,
                    "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                    "results_count":     len(flights),
                    "model_used":        MODEL_NAME,
                },
                "flights": flights
            }

        if not flights:
            job_id = get_flights_api(cursor, conn, departure_city, arrival_city, match_date_exact)

            if not job_id:
                return {
                    "meta": {
                        "match_id":          match_id,
                        "destination_city":  arrival_city,
                        "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                        "results_count":     0,
                        "model_used":        MODEL_NAME,
                    },
                    "flights": []
                }

            wait_to_spark(cursor, job_id)
            enrich_airports(cursor, conn)
            flights = check_flight_db(cursor, departure_city, arrival_city, match_date_exact)
            flights = predict_delay(cursor, flights)

            cursor.close()
            conn.close()

            return {
                "meta": {
                    "match_id":          match_id,
                    "destination_city":  arrival_city,
                    "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                    "results_count":     len(flights),
                    "model_used":        MODEL_NAME,
                },
                "flights": flights
            }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/matches")
def get_matches():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            m.match_id,
            m.match_date,
            m.id_team_a,
            ta.team_name as name_team_a,
            ta.flag      as flag_team_a,
            m.id_team_b,
            tb.team_name as name_team_b,
            tb.flag      as flag_team_b,
            m.stage,
            c.city as city_name
        FROM FACT_MATCHS m
        JOIN DIM_TEAM ta ON m.id_team_a = ta.id_team
        JOIN DIM_TEAM tb ON m.id_team_b = tb.id_team
        JOIN DIM_CITY c  ON m.id_city   = c.id_city
        ORDER BY m.match_date ASC;
    """)
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    return matches


@app.get("/api/teams")
def get_teams():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_name, team_code, flag
        FROM DIM_TEAM;
    """)
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return teams


@app.get("/api/cities")
def get_cities():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            c.id_city,
            c.city,
            c.country,
            c.flag,
            array_agg(a.iata_code) as airport_codes
        FROM DIM_CITY c
        LEFT JOIN DIM_AIRPORT a ON c.id_city = a.id_city
        WHERE c.is_host_city = TRUE
        GROUP BY c.id_city, c.city, c.country
        ORDER BY c.city ASC;
    """)
    cities = cursor.fetchall()
    cursor.close()
    conn.close()
    return cities

@app.get("/api/test")
def get_test():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * from fact_flight;")
    return cursor.fetchall()
