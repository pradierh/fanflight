"""
download_bts.py
---------------
Télécharge les données réelles de ponctualité des vols US depuis le BTS
(Bureau of Transportation Statistics), les filtre sur les vols ARRIVANT dans
une ville hôte de la Coupe du Monde, et les charge dans la table BTS_FLIGHTS.

Source : BTS On-Time Reporting Carrier Performance
URL pattern : https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{YEAR}_{MONTH}.zip

Période : mai, juin, juillet 2025 (trimestre estival, aligné avec juin 2026).

Label métier (calculé ici) :
    is_delayed = 1 si ArrDelayMinutes > 15 OU Cancelled = 1
                 0 sinon

IMPORTANT — réseau Docker :
    transtats.bts.gov n'est probablement PAS dans la liste blanche réseau du
    conteneur. Deux options :
      A) Télécharger les zip à la main sur ta machine Windows, les placer dans
         data-pipeline/data/bts_raw/, et lancer ce script avec --from-local
      B) Ajouter transtats.bts.gov aux domaines autorisés du conteneur

Usage :
    python download_bts.py                 # télécharge depuis BTS
    python download_bts.py --from-local    # lit les zip déjà téléchargés
"""

import argparse
import io
import logging
import os
import zipfile
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

BTS_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

# Période d'entraînement : trimestre estival 2025
PERIODS = [(2025, 5), (2025, 6), (2025, 7)]

# Aéroports US des villes Coupe du Monde (destination = arrivée)
WC_ARRIVAL_AIRPORTS = [
    "EWR", "JFK", "LGA",          # New York
    "LAX", "BUR", "SNA", "LGB",   # Los Angeles
    "SFO", "SJC", "OAK",          # San Francisco
    "DFW", "DAL",                 # Dallas
    "MIA", "FLL",                 # Miami
    "IAH", "HOU",                 # Houston
    "ATL",                        # Atlanta
    "SEA", "BFI",                 # Seattle
    "BOS",                        # Boston
    "PHL",                        # Philadelphie
    "MCI",                        # Kansas City
]

# Colonnes BTS qu'on garde (sur les ~109 disponibles)
BTS_COLUMNS = [
    "FlightDate",
    "Reporting_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",        # heure prévue de départ (format HHMM)
    "CRSArrTime",        # heure prévue d'arrivée
    "DepDelay",
    "ArrDelay",
    "ArrDelayMinutes",
    "Cancelled",
    "Diverted",
    "Distance",
    "WeatherDelay",
    "CarrierDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
]

LOCAL_DIR = Path(os.getenv("DATA_DIR", "/opt/data")) / "bts_raw"
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

DELAY_THRESHOLD_MIN = 15  # seuil officiel BTS


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
    )


# ------------------------------------------------------------------
# Table
# ------------------------------------------------------------------

def create_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BTS_FLIGHTS (
            id             SERIAL PRIMARY KEY,
            flight_date    DATE,
            airline        VARCHAR(10),
            origin         VARCHAR(10),
            dest           VARCHAR(10),
            crs_dep_time   INTEGER,
            crs_arr_time   INTEGER,
            dep_delay      REAL,
            arr_delay      REAL,
            arr_delay_min  REAL,
            cancelled      REAL,
            diverted       REAL,
            distance       REAL,
            weather_delay  REAL,
            carrier_delay  REAL,
            nas_delay      REAL,
            security_delay REAL,
            late_aircraft_delay REAL,
            is_delayed     INTEGER,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cursor.close()


# ------------------------------------------------------------------
# Téléchargement / lecture
# ------------------------------------------------------------------

def get_zip_bytes(year: int, month: int, from_local: bool) -> bytes | None:
    local_path = LOCAL_DIR / f"bts_{year}_{month}.zip"

    if from_local:
        if local_path.exists():
            log.info(f"Lecture locale : {local_path}")
            return local_path.read_bytes()
        log.error(f"Fichier local absent : {local_path}")
        return None

    url = BTS_URL_TEMPLATE.format(year=year, month=month)
    log.info(f"Téléchargement : {url}")
    try:
        # timeout généreux : les serveurs BTS sont lents
        resp = requests.get(url, timeout=300, verify=False)
        resp.raise_for_status()
        # Sauvegarde locale pour réutilisation
        local_path.write_bytes(resp.content)
        log.info(f"Sauvegardé localement : {local_path} ({len(resp.content)//1024//1024} Mo)")
        return resp.content
    except requests.exceptions.RequestException as e:
        log.error(f"Échec téléchargement {year}-{month} : {e}")
        log.error("Astuce : télécharge le zip à la main et utilise --from-local")
        return None


def parse_zip(zip_bytes: bytes) -> pd.DataFrame | None:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # Le CSV est le seul fichier .csv du zip
            csv_name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
            with z.open(csv_name) as f:
                # On ne lit que les colonnes utiles pour économiser la mémoire
                df = pd.read_csv(f, usecols=lambda c: c in BTS_COLUMNS, low_memory=False)
        return df
    except Exception as e:
        log.error(f"Erreur lecture zip : {e}")
        return None


# ------------------------------------------------------------------
# Traitement et insertion
# ------------------------------------------------------------------

def process_and_insert(conn, df: pd.DataFrame):
    # Filtre : vols arrivant dans une ville Coupe du Monde
    df = df[df["Dest"].isin(WC_ARRIVAL_AIRPORTS)].copy()
    log.info(f"  Après filtre destinations Coupe du Monde : {len(df)} vols")

    if df.empty:
        return 0

    # Label métier : retard > 15 min OU annulé
    df["ArrDelayMinutes"] = pd.to_numeric(df["ArrDelayMinutes"], errors="coerce")
    df["Cancelled"]       = pd.to_numeric(df["Cancelled"], errors="coerce").fillna(0)
    df["is_delayed"] = (
        (df["ArrDelayMinutes"] > DELAY_THRESHOLD_MIN) | (df["Cancelled"] == 1)
    ).astype(int)

    # Préparation des lignes
    def safe(v):
        return None if pd.isna(v) else v

    rows = []
    for _, r in df.iterrows():
        rows.append((
            safe(r.get("FlightDate")),
            safe(r.get("Reporting_Airline")),
            safe(r.get("Origin")),
            safe(r.get("Dest")),
            safe(r.get("CRSDepTime")),
            safe(r.get("CRSArrTime")),
            safe(r.get("DepDelay")),
            safe(r.get("ArrDelay")),
            safe(r.get("ArrDelayMinutes")),
            safe(r.get("Cancelled")),
            safe(r.get("Diverted")),
            safe(r.get("Distance")),
            safe(r.get("WeatherDelay")),
            safe(r.get("CarrierDelay")),
            safe(r.get("NASDelay")),
            safe(r.get("SecurityDelay")),
            safe(r.get("LateAircraftDelay")),
            int(r["is_delayed"]),
        ))

    cursor = conn.cursor()
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO BTS_FLIGHTS (
            flight_date, airline, origin, dest, crs_dep_time, crs_arr_time,
            dep_delay, arr_delay, arr_delay_min, cancelled, diverted, distance,
            weather_delay, carrier_delay, nas_delay, security_delay,
            late_aircraft_delay, is_delayed
        ) VALUES %s
        """,
        rows,
        page_size=1000,
    )
    conn.commit()
    cursor.close()
    return len(rows)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def run(from_local: bool):
    # Supprime le warning SSL de verify=False
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    conn = get_conn()
    create_table(conn)

    # On vide la table pour repartir propre (idempotent)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE BTS_FLIGHTS RESTART IDENTITY;")
    conn.commit()
    cursor.close()

    total = 0
    for year, month in PERIODS:
        zip_bytes = get_zip_bytes(year, month, from_local)
        if zip_bytes is None:
            continue
        df = parse_zip(zip_bytes)
        if df is None:
            continue
        log.info(f"{year}-{month:02d} : {len(df)} vols bruts")
        n = process_and_insert(conn, df)
        total += n
        log.info(f"{year}-{month:02d} : {n} vols insérés")

    # Stats finales
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(is_delayed) FROM bts_flights;")
    cnt, delayed = cursor.fetchone()
    cursor.close()
    conn.close()

    log.info(f"\nTotal inséré : {total} vols")
    if cnt:
        log.info(f"Vols en retard/annulés : {delayed}/{cnt} ({100*delayed/cnt:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-local", action="store_true",
                        help="Lit les zip déjà téléchargés dans data/bts_raw/")
    args = parser.parse_args()
    run(from_local=args.from_local)
