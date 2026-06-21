import os
from datetime import datetime, timedelta
import time
from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json

# --- ML / inférence ---
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

# Variables globales chargées au démarrage
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
# CHARGEMENT DU MODÈLE AU DÉMARRAGE
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
        print(f"[ML] Mappings introuvables ({e}) — prédictions désactivées.")
        MAPPINGS = None

    # Chargement direct du booster XGBoost (contourne le bug _estimator_type)
    try:
        import xgboost as xgb
        from mlflow.tracking import MlflowClient

        client = MlflowClient()
        # Récupère la dernière version du modèle xgboost (peu importe le stage)
        versions = client.get_latest_versions("flight_delay_xgboost")
        if not versions:
            raise Exception("Aucune version de flight_delay_xgboost")
        # Prend la version au numéro le plus élevé
        latest = max(versions, key=lambda v: int(v.version))
        run_id = latest.run_id

        # Chemin local de l'artefact (le volume est partagé)
        local_path = client.download_artifacts(run_id, "model/model.xgb")
        print(f"[ML] Artefact téléchargé : {local_path}")

        booster = xgb.Booster()
        booster.load_model(local_path)
        MODEL = booster
        MODEL_NAME = "xgboost"
        print(f"[ML] Booster XGBoost chargé (version {latest.version})")
        return
    except Exception as e:
        print(f"[ML] Échec chargement booster XGBoost : {e}")

    print("[ML] Aucun modèle disponible — l'API renvoie les vols sans score.")
    MODEL = None


# ==================================================================
# MÉTÉO POUR L'INFÉRENCE
# ==================================================================

def get_weather_for_inference(cursor, flight):
    """
    Récupère la météo d'un vol pour la prédiction.
    1) D'abord depuis FACT_FLIGHT_WEATHER (déjà enrichie par fetch_weather.py).
    2) Sinon, valeurs par défaut neutres (le vol est quand même scoré).
    """
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
    return None  # build_features_for_flight appliquera les défauts


def predict_delay(cursor, flights):
    """
    Ajoute le champ 'delay_probability' (0..1) et 'delay_prediction' (bool)
    à chaque vol. Si le modèle n'est pas chargé, met les champs à None.
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

    # pyfunc.predict : selon le modèle, renvoie proba ou classe.
    # On passe par un DataFrame avec les bons noms de colonnes pour XGBoost.
    import pandas as pd
    import xgboost as xgb
    X_df = pd.DataFrame(X, columns=FEATURE_COLS)

    try:
        # Booster brut : prédit via DMatrix, renvoie directement la proba
        dmatrix = xgb.DMatrix(X_df)
        preds = MODEL.predict(dmatrix)
        preds = np.asarray(preds).ravel()
    except Exception as e:
        print(f"[ML] Erreur de prédiction : {e}")
        for f in flights:
            f["delay_probability"] = None
            f["delay_prediction"] = None
            f["model_used"] = MODEL_NAME
        return flights

    for f, p in zip(flights, preds):
        prob = float(p)
        # Si le modèle renvoie une classe 0/1 plutôt qu'une proba, on la garde telle quelle
        prob = max(0.0, min(1.0, prob))
        f["delay_probability"] = round(prob, 4)
        f["delay_prediction"] = bool(prob >= 0.5)
        f["model_used"] = MODEL_NAME

    return flights


# ==================================================================
# LOGIQUE EXISTANTE — recherche de vols
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
def get_flights(match_id: int, departure_city: str):
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
        match_date_exact = match_info['match_date']

        vols = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)

        if not vols:
            job_id = get_flights_api(cursor, conn, departure_city, match_info['arrival_city'], match_date_exact)
            wait_to_spark(cursor, job_id)
            vols = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)

        # --- PRÉDICTION DU RETARD POUR CHAQUE VOL ---
        vols = predict_delay(cursor, vols)

        cursor.close()
        conn.close()

        return {
            "meta": {
                "match_id": match_id,
                "departure_city": departure_city,
                "destination_city": match_info['arrival_city'],
                "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                "results_count": len(vols),
                "model_used": MODEL_NAME,
            },
            "flights": vols
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Endpoint de vérification : indique si le modèle est chargé."""
    return {
        "status": "ok",
        "model_loaded": MODEL is not None,
        "model_name": MODEL_NAME,
        "mappings_loaded": MAPPINGS is not None,
    }
