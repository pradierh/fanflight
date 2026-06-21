"""
build_training_set.py
----------------------
Assemble le dataset d'entraînement ML en joinant FACT_FLIGHT et FACT_FLIGHT_WEATHER.

Features produites :
  Catégorielles  : airline, departure_airport_id, arrival_airport_id, airplane_type
  Numériques     : duration, layover_duration, total_journey_duration, price,
                   hour_of_day, day_of_week, is_best, pos,
                   temperature_c, precipitation_mm, wind_speed_kmh,
                   visibility_m, snowfall_cm, weather_code
  Dérivées       : is_overnight, has_layover, weather_risk_score

Label : is_delayed (BOOLEAN depuis FACT_FLIGHT, source = Google Flights
        champ "often_delayed_by_over_30_min")

Output : data/training_set.parquet  (et training_set.csv pour inspection)
"""

import os
import logging
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("DATA_DIR", "/opt/spark/data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# WMO weather code -> risk score numérique (0 = clair, 3 = critique)
# Permet au modèle de traiter le code météo comme un ordinal.
# ------------------------------------------------------------------
WMO_RISK = {
    0: 0, 1: 0, 2: 0, 3: 0,          # Clair / nuageux
    45: 2, 48: 2,                      # Brouillard
    51: 1, 53: 1, 55: 2,              # Bruine
    61: 1, 63: 2, 65: 2,              # Pluie
    71: 2, 73: 2, 75: 3,              # Neige
    80: 1, 81: 2, 82: 2,              # Averses
    95: 3, 96: 3, 99: 3,              # Orage
}


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


QUERY = """
    SELECT
        -- Identifiants (ne sont pas des features, utilisés pour traçabilité)
        f.flight_sk,
        f.journey_sk,

        -- Features vol
        f.airline,
        f.departure_airport_id,
        f.arrival_airport_id,
        f.duration,
        f.layover_duration,
        f.total_journey_duration,
        f.price,
        f.is_best,
        f.pos,
        f.departure_airport_time,

        -- Features météo (NULL si non enrichi)
        w.temperature_c,
        w.precipitation_mm,
        w.weather_code,
        w.wind_speed_kmh,
        w.visibility_m,
        w.snowfall_cm,

        -- Label
        f.is_delayed

    FROM fact_flight f
    LEFT JOIN fact_flight_weather w ON f.flight_sk = w.flight_sk
    ORDER BY f.departure_airport_time;
"""


def build():
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute(QUERY)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        log.error("Aucune donnée dans FACT_FLIGHT. Lance d'abord le pipeline Spark.")
        return

    df = pd.DataFrame(rows)
    log.info(f"Lignes brutes : {len(df)}")

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    # Heure et jour de départ
    df["departure_airport_time"] = pd.to_datetime(df["departure_airport_time"])
    df["hour_of_day"]  = df["departure_airport_time"].dt.hour
    df["day_of_week"]  = df["departure_airport_time"].dt.dayofweek  # 0=lundi … 6=dimanche

    # Flags dérivés
    df["is_overnight"] = ((df["hour_of_day"] >= 21) | (df["hour_of_day"] <= 5)).astype(int)
    df["has_layover"]  = (df["layover_duration"].fillna(0) > 0).astype(int)
    df["is_best"]      = df["is_best"].fillna(False).astype(int)

    # Score de risque météo (WMO -> ordinal)
    df["weather_risk_score"] = df["weather_code"].map(WMO_RISK).fillna(0).astype(int)

    # Imputations simples pour les vols sans météo
    # (médiane pour les numériques, 0 pour le risque)
    weather_defaults = {
        "temperature_c": 20.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 10.0,
        "visibility_m": 10000.0,
        "snowfall_cm": 0.0,
    }
    for col, default in weather_defaults.items():
        median_val = df[col].median()
        fill_value = median_val if pd.notna(median_val) else default
        df[col] = df[col].fillna(fill_value)
    df["weather_code"] = df["weather_code"].fillna(0).astype(int)

    # Encodage de l'airline (label encoding simple — XGBoost et PyTorch gèrent bien)
    df["airline_code"] = df["airline"].astype("category").cat.codes
    df["dep_airport_code"] = df["departure_airport_id"].astype("category").cat.codes
    df["arr_airport_code"] = df["arrival_airport_id"].astype("category").cat.codes

    # Label en int
    df["is_delayed"] = df["is_delayed"].fillna(False).astype(int)

    # ------------------------------------------------------------------
    # Colonnes finales
    # ------------------------------------------------------------------

    FEATURE_COLS = [
        # Numériques vol
        "duration", "layover_duration", "total_journey_duration", "price",
        "hour_of_day", "day_of_week", "pos",
        # Flags
        "is_best", "is_overnight", "has_layover",
        # Catégorielles encodées
        "airline_code", "dep_airport_code", "arr_airport_code",
        # Météo
        "temperature_c", "precipitation_mm", "weather_code",
        "wind_speed_kmh", "visibility_m", "snowfall_cm", "weather_risk_score",
    ]
    LABEL_COL = "is_delayed"
    ID_COLS   = ["flight_sk", "journey_sk", "airline", "departure_airport_id", "arrival_airport_id"]

    df_out = df[ID_COLS + FEATURE_COLS + [LABEL_COL]].copy()

    # Remplir les NaN restants (layover_duration peut être NULL pour vol direct)
    df_out["layover_duration"] = df_out["layover_duration"].fillna(0)
    df_out = df_out.dropna(subset=FEATURE_COLS + [LABEL_COL])
    
    # Force les colonnes numériques en float (évite les types Decimal/object
    # venant de Postgres qui font échouer l'écriture parquet)
    numeric_cols = [
        "duration", "layover_duration", "total_journey_duration", "price",
        "hour_of_day", "day_of_week", "pos",
        "is_best", "is_overnight", "has_layover",
        "airline_code", "dep_airport_code", "arr_airport_code",
        "temperature_c", "precipitation_mm", "weather_code",
        "wind_speed_kmh", "visibility_m", "snowfall_cm", "weather_risk_score",
        "is_delayed",
    ]
    for col in numeric_cols:
        df_out[col] = pd.to_numeric(df_out[col], errors="coerce").astype(float)
    log.info(f"Dataset final : {len(df_out)} lignes, {len(FEATURE_COLS)} features")
    log.info(f"Taux de retard : {df_out[LABEL_COL].mean():.1%}")
    log.info(f"Distribution label :\n{df_out[LABEL_COL].value_counts()}")

    # Sauvegarde
    parquet_path = OUTPUT_DIR / "training_set.parquet"
    csv_path     = OUTPUT_DIR / "training_set.csv"

    df_out.to_parquet(parquet_path, index=False)
    df_out.to_csv(csv_path, index=False)

    log.info(f"Sauvegardé : {parquet_path}")
    log.info(f"Sauvegardé : {csv_path}")

    return df_out


if __name__ == "__main__":
    build()
