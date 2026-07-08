import os
from datetime import datetime, timedelta
import time
from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json

# --- ML / inference ---
import mlflow.xgboost
import mlflow
import mlflow.pyfunc
import numpy as np
from pathlib import Path
from feature_builder import (
    FEATURE_COLS, WEATHER_DEFAULTS,
    load_mappings, build_features_for_flight, features_to_vector,
)


app = FastAPI(title="API de Vols - Coupe du Monde 2026")

API_KEY = os.getenv("API_KEY_SERAPI")

# ------------------------------------------------------------------
# Configuration ML
# ------------------------------------------------------------------
MLFLOW_URI       = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
DATA_DIR         = Path(os.getenv("DATA_DIR", "/opt/data"))
MAPPINGS_PATH    = DATA_DIR / "category_mappings.json"
PROD_MODEL_XGB   = "models:/flight_delay_xgboost/Production"
PROD_MODEL_NN    = "models:/flight_delay_nn/Production"

# ------------------------------------------------------------------
# Configuration meteo (prevision Open-Meteo)
# ------------------------------------------------------------------
FORECAST_URL         = "https://api.open-meteo.com/v1/forecast"
FORECAST_HOURLY      = "temperature_2m,precipitation,weather_code,wind_speed_10m,visibility,snowfall"
FORECAST_WINDOW_DAYS = 16  # limite de prevision Open-Meteo

# Variables globales chargees au demarrage
MODEL = None
MAPPINGS = None
MODEL_NAME = None


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
# CHARGEMENT DU MODELE AU DEMARRAGE
# ==================================================================

@app.on_event("startup")
def load_model():
    global MODEL, MAPPINGS, MODEL_NAME
    mlflow.set_tracking_uri(MLFLOW_URI)

    # Mappings d'encodage
    try:
        MAPPINGS = load_mappings(MAPPINGS_PATH)
        print(f"[ML] Mappings charges depuis {MAPPINGS_PATH}")
    except Exception as e:
        print(f"[ML] Mappings introuvables ({e}) - predictions desactivees.")
        MAPPINGS = None

    # Chargement direct du booster XGBoost (contourne le bug _estimator_type)
    try:
        import xgboost as xgb
        from mlflow.tracking import MlflowClient

        client = MlflowClient()
        versions = client.get_latest_versions("flight_delay_xgboost")
        if not versions:
            raise Exception("Aucune version de flight_delay_xgboost")
        latest = max(versions, key=lambda v: int(v.version))
        run_id = latest.run_id

        local_path = client.download_artifacts(run_id, "model/model.xgb")
        print(f"[ML] Artefact telecharge : {local_path}")

        booster = xgb.Booster()
        booster.load_model(local_path)
        MODEL = booster
        MODEL_NAME = "xgboost"
        print(f"[ML] Booster XGBoost charge (version {latest.version})")
        return
    except Exception as e:
        print(f"[ML] Echec chargement booster XGBoost : {e}")

    print("[ML] Aucun modele disponible - l'API renvoie les vols sans score.")
    MODEL = None


# ==================================================================
# METEO POUR L'INFERENCE
# ==================================================================

def get_airport_coords(cursor, iata_code):
    """Coordonnees d'un aeroport depuis DIM_AIRPORT."""
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
    Recupere la prevision meteo reelle pour une date/heure de vol proche,
    a l'aeroport d'arrivee. Retourne un dict meteo ou None si indisponible.
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
        print(f"[ML] Prevision meteo indisponible : {e}")
        return None


def get_weather_for_inference(cursor, flight):
    """
    Recupere la meteo d'un vol pour la prediction, avec strategie en cascade :
    1) Si le vol est dans la fenetre de prevision (<= 16 jours), prevision REELLE
       Open-Meteo a l'aeroport d'arrivee.
    2) Sinon, repli sur FACT_FLIGHT_WEATHER (approximation saisonniere N-1).
    3) Sinon, valeurs par defaut (gerees en aval par build_features_for_flight).
    """
    dep_time = flight.get("departure_airport_time")
    if isinstance(dep_time, str):
        dep_time = datetime.fromisoformat(dep_time)

    if dep_time is not None:
        now = datetime.now(dep_time.tzinfo) if dep_time.tzinfo else datetime.now()
        days_ahead = (dep_time - now).days

        # 1) Vol proche -> prevision reelle a l'aeroport d'arrivee
        if 0 <= days_ahead <= FORECAST_WINDOW_DAYS:
            coords = get_airport_coords(cursor, flight["arrival_airport_id"])
            if coords:
                forecast = fetch_forecast_weather(coords[0], coords[1], dep_time)
                if forecast and forecast.get("temperature_c") is not None:
                    return forecast

    # 2) Repli : meteo pre-enrichie en base
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

    # 3) Rien -> les defauts s'appliqueront
    return None


def clean_unused_cols(flights):
    """Supprime les champs internes non destinés à l'API publique."""
    for flight in flights:
        flight.pop("is_delayed", None)
    return flights


def predict_delay(cursor, flights):
    """
    Ajoute le champ 'delay_probability' (0..1) et 'delay_prediction' (bool)
    a chaque vol. Si le modele n'est pas charge, met les champs a None.
    """
    if MODEL is None or MAPPINGS is None:
        for f in flights:
            f["delay_probability"] = None
            f["delay_prediction"] = None
            f["model_used"] = None
        return flights

    # Construit la matrice de features pour tous les vols d'un coup
    rows = []
    for f in flights:
        weather = get_weather_for_inference(cursor, f)
        feats = build_features_for_flight(f, weather, MAPPINGS)
        rows.append(features_to_vector(feats))

    X = np.array(rows, dtype=np.float32)

    import pandas as pd
    import xgboost as xgb
    X_df = pd.DataFrame(X, columns=FEATURE_COLS)

    try:
        # Booster brut : predit via DMatrix, renvoie directement la proba
        dmatrix = xgb.DMatrix(X_df)
        preds = MODEL.predict(dmatrix)
        preds = np.asarray(preds).ravel()
    except Exception as e:
        print(f"[ML] Erreur de prediction : {e}")
        for f in flights:
            f["delay_probability"] = None
            f["delay_prediction"] = None
            f["model_used"] = MODEL_NAME
        return flights

    for f, p in zip(flights, preds):
        prob = float(p)
        prob = max(0.0, min(1.0, prob))
        f["delay_probability"] = round(prob, 4)
        f["delay_prediction"] = bool(prob >= 0.5)
        f["model_used"] = MODEL_NAME

    return flights


# ==================================================================
# LOGIQUE EXISTANTE - recherche de vols
# ==================================================================

def check_flight_db(cursor, departure_city, arrival_city, match_date_exact):
    flights_query = """
    WITH CTE_DEPARTURE_FLIGHT as(
        select journey_sk
        from FACT_FLIGHT f
        JOIN DIM_AIRPORT dep_a ON f.departure_airport_id = dep_a.iata_code
        JOIN DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
        WHERE LOWER(dep_c.city) = LOWER(%s) and f.pos = 0
        )
        , CTE_ARRIVAL_FLIGHT as (
        select journey_sk
        from fact_flight f
        JOIN DIM_AIRPORT arr_a ON f.arrival_airport_id = arr_a.iata_code
        JOIN DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
        WHERE LOWER(arr_c.city) = LOWER(%s)
        )
        , UNIONED as (
        select df.journey_sk
        from CTE_DEPARTURE_FLIGHT df
        join CTE_ARRIVAL_FLIGHT af on df.journey_sk = af.journey_sk
        )
        SELECT
            f.flight_sk, f.journey_sk,
            dep_c.city as departure_city, f.departure_airport_id, f.departure_airport_time,
            arr_c.city as arrival_city, f.arrival_airport_id, f.arrival_airport_time,
            f.duration, f.layover_duration, f.total_journey_duration,
            f.price, f.airline, f.is_best, f.pos
        FROM FACT_FLIGHT f
        join UNIONED u on f.journey_sk = u.journey_sk
        JOIN DIM_AIRPORT dep_a ON f.departure_airport_id = dep_a.iata_code
        JOIN DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
        JOIN DIM_AIRPORT arr_a ON f.arrival_airport_id = arr_a.iata_code
        JOIN DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
        WHERE f.arrival_airport_time BETWEEN (%s::date - INTERVAL '3 days') AND (%s - INTERVAL '5 hours')
        ORDER BY journey_sk, departure_airport_time asc;
        """
    cursor.execute(flights_query, (departure_city, arrival_city, match_date_exact, match_date_exact))
    return cursor.fetchall()


# ------------------------------------------------------------------
# REGISTRE DES TRAJETS DEJA INTERROGES (anti-gaspillage de quota API)
# ------------------------------------------------------------------

def route_already_queried(cursor, departure_city, arrival_city, match_id):
    """
    Retourne True si ce trajet (depart, arrivee, match) a deja ete interroge
    aupres de SerpAPI. Dans ce cas, on ne rappelle jamais l'API.
    """
    cursor.execute(
        """
        SELECT 1 FROM queried_routes
        WHERE LOWER(departure_city) = LOWER(%s)
          AND LOWER(arrival_city)   = LOWER(%s)
          AND match_id = %s
        """,
        (departure_city, arrival_city, match_id),
    )
    return cursor.fetchone() is not None


def mark_route_queried(cursor, conn, departure_city, arrival_city, match_id, flights_found):
    """
    Enregistre le trajet comme interroge, quel que soit le nombre de vols trouves.
    ON CONFLICT DO NOTHING : idempotent, jamais de doublon.
    """
    cursor.execute(
        """
        INSERT INTO queried_routes (departure_city, arrival_city, match_id, flights_found)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT ON CONSTRAINT unique_route_query DO NOTHING
        """,
        (departure_city, arrival_city, match_id, flights_found),
    )
    conn.commit()


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
            detail="Impossible de trouver les codes aeroports (IATA) pour ces villes dans le dictionnaire."
        )

    all_flights_raw = []
    for aero_dep in aeroports_depart:
        code_iata_depart = aero_dep['iata_code']
        for aero_arr in aeroports_arrivee:
            code_iata_arrivee = aero_arr['iata_code']
            for day in range(2):
                date_vol = (match_date_exact - timedelta(days=day + 1)).date()
                params = {
                    "engine": "google_flights",
                    "type": "2",
                    "departure_id": code_iata_depart,
                    "arrival_id": code_iata_arrivee,
                    "outbound_date": date_vol,
                    "currency": "EUR",
                    "hl": "fr",
                    "api_key": API_KEY
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
    start = time.time()
    timeout = 120
    while True:
        if time.time() - start > timeout:
            raise Exception("Timeout")
        cursor.execute(
            "SELECT bool_and(processed) as is_done FROM flights_raw WHERE id = ANY(%s)", ([job_id],)
        )
        row = cursor.fetchone()
        if row and row['is_done'] == True:
            return True
        time.sleep(2)


@app.get("/api/flights/{match_id}")
def get_flights(match_id: int, departure_city: str, force: bool = False):
    """
    Renvoie les vols pour un match + la probabilite de retard de chaque vol.

    Gestion du quota SerpAPI via le registre queried_routes :
      - Si le trajet a deja ete interroge, on lit UNIQUEMENT la base (jamais l'API),
        meme si la base est vide pour ce trajet.
      - Sinon, on appelle l'API une fois puis on enregistre le trajet.
      - Le parametre ?force=true permet de forcer un rappel API malgre le registre
        (utile pour les tests ou un rafraichissement volontaire).
    """
    try:
        conn = get_db_connection()
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
        arrival_city = match_info['arrival_city']

        already_queried = route_already_queried(cursor, departure_city, arrival_city, match_id)

        if already_queried and not force:
            # Trajet deja interroge : lecture base uniquement, aucun appel API
            print(f"[CACHE] Trajet deja interroge ({departure_city} -> {arrival_city}, match {match_id}). Lecture base.")
            vols = check_flight_db(cursor, departure_city, arrival_city, match_date_exact)
        else:
            # Premier appel (ou force) : on regarde la base, puis l'API si besoin
            vols = check_flight_db(cursor, departure_city, arrival_city, match_date_exact)
            if not vols or force:
                print(f"[API] Appel SerpAPI ({departure_city} -> {arrival_city}, match {match_id}).")
                job_id = get_flights_api(cursor, conn, departure_city, arrival_city, match_date_exact)
                wait_to_spark(cursor, job_id)
                vols = check_flight_db(cursor, departure_city, arrival_city, match_date_exact)

            # On enregistre le trajet comme interroge, quel que soit le resultat
            mark_route_queried(cursor, conn, departure_city, arrival_city, match_id, len(vols))

        # --- PREDICTION DU RETARD POUR CHAQUE VOL ---
        vols = predict_delay(cursor, vols)
        vols = clean_unused_cols(vols)

        cursor.close()
        conn.close()

        return {
            "meta": {
                "match_id": match_id,
                "departure_city": departure_city,
                "destination_city": arrival_city,
                "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                "results_count": len(vols),
                "model_used": MODEL_NAME,
                "from_cache": already_queried and not force,
            },
            "flights": vols
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Endpoint de verification : indique si le modele est charge."""
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_name": MODEL_NAME,
        "mappings_loaded": MAPPINGS is not None,
    }
