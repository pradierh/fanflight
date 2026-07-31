"""
build_training_set_bts.py
-------------------------
Construit le dataset d'entraînement à partir des données RÉELLES BTS 2025
enrichies de la météo réelle du même jour.

C'est la version rigoureuse de build_training_set.py :
    - vols réellement effectués (BTS, mai-juin-juillet 2025)
    - retard réellement observé (label honnête : ArrDelayMinutes > 15 OU annulé)
    - météo réelle du jour du vol (alignement causal)

Features alignées avec feature_builder.FEATURE_COLS pour rester compatible
avec train.py et l'inférence.

Output : data/training_set.parquet + category_mappings.json
         (écrase l'ancien dataset Google/2026)
"""

import logging
import os
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

from feature_builder import (
    FEATURE_COLS, LABEL_COL, WMO_RISK, WEATHER_DEFAULTS,
    build_category_mappings, encode_category, save_mappings,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.getenv("DATA_DIR", "/opt/data"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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
        airline,
        origin AS departure_airport_code,
        dest   AS arrival_airport_code,
        crs_dep_time,
        crs_arr_time,
        distance,
        flight_date,
        temperature_c,
        precipitation_mm,
        weather_code,
        wind_speed_kmh,
        visibility_m,
        snowfall_cm,
        is_delayed
    FROM bts_flights;
"""


def crs_to_hour(v):
    if pd.isna(v):
        return 12
    try:
        return min(23, int(v) // 100)
    except (ValueError, TypeError):
        return 12


def build():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(QUERY)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        log.error("BTS_FLIGHTS vide. Lance download_bts.py puis enrich_bts_weather.py.")
        return

    df = pd.DataFrame(rows)
    log.info(f"Lignes brutes BTS : {len(df)}")

    # ------------------------------------------------------------------
    # Feature engineering — aligné sur feature_builder.FEATURE_COLS
    # ------------------------------------------------------------------

    df["flight_date"] = pd.to_datetime(df["flight_date"])
    df["hour_of_day"] = df["crs_dep_time"].map(crs_to_hour)
    df["day_of_week"] = df["flight_date"].dt.dayofweek

    df["is_overnight"] = ((df["hour_of_day"] >= 21) | (df["hour_of_day"] <= 5)).astype(int)

    # BTS = vols directs : pas de correspondance, donc layover et pos à 0
    df["layover_duration"]       = 0.0
    df["has_layover"]            = 0
    df["pos"]                    = 0.0
    df["is_best"]                = 0  # notion propre à SerpAPI, neutre ici

    # Durée et "total" : on utilise la distance comme proxy de durée (pas de temps de vol direct dans nos colonnes)
    # Le BTS a CRSElapsedTime mais on ne l'a pas chargé ; on dérive de la distance.
    # Approximation : ~ distance / 7 (vitesse de croisière en miles/min approx) — proxy grossier mais cohérent.
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(df["distance"].median())
    df["duration"] = (df["distance"] / 7.0).round()
    df["total_journey_duration"] = df["duration"]

    # Prix : absent du BTS. On met une valeur neutre constante (le modèle l'ignorera).
    # Alternative honnête : retirer 'price' des features. Ici on met la médiane d'un prix plausible.
    df["price"] = 200.0

    # Météo : valeurs par défaut si manquante
    for col, default in WEATHER_DEFAULTS.items():
        if col == "weather_code":
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        else:
            med = pd.to_numeric(df[col], errors="coerce").median()
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(med if pd.notna(med) else default)

    df["weather_risk_score"] = df["weather_code"].map(WMO_RISK).fillna(0).astype(int)

    # Encodage catégoriel via le mapping partagé
    mappings = build_category_mappings(df)
    df["airline_code"]     = df["airline"].map(lambda v: encode_category(v, mappings["airline"]))
    df["dep_airport_code"] = df["departure_airport_code"].map(lambda v: encode_category(v, mappings["departure_airport_code"]))
    df["arr_airport_code"] = df["arrival_airport_code"].map(lambda v: encode_category(v, mappings["arrival_airport_code"]))

    df["is_delayed"] = df["is_delayed"].astype(int)

    # ------------------------------------------------------------------
    # Sélection finale
    # ------------------------------------------------------------------
    ID_COLS = ["airline", "departure_airport_code", "arrival_airport_code"]
    df_out = df[ID_COLS + FEATURE_COLS + [LABEL_COL]].copy()

    # Types numériques propres pour parquet
    for col in FEATURE_COLS + [LABEL_COL]:
        df_out[col] = pd.to_numeric(df_out[col], errors="coerce").astype(float)

    df_out = df_out.dropna(subset=FEATURE_COLS + [LABEL_COL])

    log.info(f"Dataset final : {len(df_out)} lignes, {len(FEATURE_COLS)} features")
    log.info(f"Taux de retard réel : {df_out[LABEL_COL].mean():.1%}")
    log.info(f"Distribution :\n{df_out[LABEL_COL].value_counts()}")

    # Sauvegarde
    parquet_path = OUTPUT_DIR / "training_set.parquet"
    csv_path     = OUTPUT_DIR / "training_set.csv"
    df_out.to_parquet(parquet_path, index=False)
    df_out.to_csv(csv_path, index=False)
    log.info(f"Sauvegardé : {parquet_path}")

    # Mappings pour l'inférence
    mappings_path = OUTPUT_DIR / "category_mappings.json"
    save_mappings(mappings, mappings_path)
    log.info(f"Sauvegardé : {mappings_path}")

    return df_out


if __name__ == "__main__":
    build()
