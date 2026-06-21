"""
enrich_bts_weather.py
---------------------
Enrichit BTS_FLIGHTS avec la météo RÉELLE du jour du vol (Open-Meteo archive).

Différence cruciale avec l'ancienne approche :
    Ici, vol et météo sont sur la MÊME date réelle (2025). Le lien est causal :
    la météo du 15 juin 2025 à l'aéroport d'arrivée correspond vraiment au vol
    du 15 juin 2025. C'est ce qui rend l'entraînement méthodologiquement valide.

On enrichit la météo à l'aéroport de DESTINATION (arrivée), car le retard
d'arrivée dépend des conditions à l'atterrissage.

Optimisation : on regroupe par (aéroport, date) pour ne pas appeler Open-Meteo
des milliers de fois. Un seul appel par couple unique, puis on associe à l'heure
prévue d'arrivée de chaque vol.

Usage :
    python enrich_bts_weather.py
"""

import logging
import os
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS    = "temperature_2m,precipitation,weather_code,wind_speed_10m,visibility,snowfall"
SLEEP          = 0.3


def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def create_weather_columns(conn):
    """Ajoute les colonnes météo à BTS_FLIGHTS si absentes."""
    cursor = conn.cursor()
    cursor.execute("""
        ALTER TABLE BTS_FLIGHTS
            ADD COLUMN IF NOT EXISTS temperature_c    REAL,
            ADD COLUMN IF NOT EXISTS precipitation_mm REAL,
            ADD COLUMN IF NOT EXISTS weather_code     INTEGER,
            ADD COLUMN IF NOT EXISTS wind_speed_kmh   REAL,
            ADD COLUMN IF NOT EXISTS visibility_m     REAL,
            ADD COLUMN IF NOT EXISTS snowfall_cm      REAL,
            ADD COLUMN IF NOT EXISTS weather_enriched BOOLEAN DEFAULT FALSE;
    """)
    conn.commit()
    cursor.close()


def get_airport_coords(conn):
    """Mapping IATA -> (lat, lon) depuis DIM_AIRPORT."""
    cursor = conn.cursor()
    cursor.execute("SELECT iata_code, latitude, longitude FROM dim_airport WHERE latitude IS NOT NULL;")
    coords = {r["iata_code"]: (float(r["latitude"]), float(r["longitude"])) for r in cursor.fetchall()}
    cursor.close()
    return coords


def get_unique_airport_dates(conn):
    """Couples (dest, flight_date) uniques à enrichir."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT dest, flight_date
        FROM bts_flights
        WHERE weather_enriched = FALSE
        ORDER BY flight_date;
    """)
    rows = cursor.fetchall()
    cursor.close()
    return rows


def fetch_weather(lat, lon, date_str):
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": date_str, "end_date": date_str,
        "hourly": HOURLY_VARS, "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=20)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        result = {}
        for i, t in enumerate(hourly.get("time", [])):
            hour = int(t.split("T")[1][:2]) if "T" in t else int(t.split(" ")[1][:2])
            result[hour] = {
                "temperature_c":    hourly.get("temperature_2m", [None]*24)[i],
                "precipitation_mm": hourly.get("precipitation", [None]*24)[i],
                "weather_code":     hourly.get("weather_code", [None]*24)[i],
                "wind_speed_kmh":   hourly.get("wind_speed_10m", [None]*24)[i],
                "visibility_m":     hourly.get("visibility", [None]*24)[i],
                "snowfall_cm":      hourly.get("snowfall", [None]*24)[i],
            }
        return result
    except requests.exceptions.RequestException as e:
        log.warning(f"Open-Meteo {lat},{lon} {date_str}: {e}")
        return None


def crs_to_hour(crs_arr_time):
    """Convertit CRSArrTime (format HHMM en int) en heure 0-23."""
    if crs_arr_time is None:
        return 12
    try:
        t = int(crs_arr_time)
        return min(23, t // 100)
    except (ValueError, TypeError):
        return 12


def run():
    conn = get_conn()
    create_weather_columns(conn)
    coords = get_airport_coords(conn)
    couples = get_unique_airport_dates(conn)

    log.info(f"{len(couples)} couples (aéroport, date) à enrichir.")

    cursor = conn.cursor()
    enriched_couples = 0

    for couple in couples:
        dest = couple["dest"]
        flight_date = couple["flight_date"]

        if dest not in coords:
            # Aéroport sans coordonnées : on marque comme traité pour ne pas boucler
            cursor.execute(
                "UPDATE bts_flights SET weather_enriched = TRUE WHERE dest = %s AND flight_date = %s",
                (dest, flight_date)
            )
            conn.commit()
            continue

        lat, lon = coords[dest]
        date_str = flight_date.strftime("%Y-%m-%d")
        hourly = fetch_weather(lat, lon, date_str)
        time.sleep(SLEEP)

        if hourly is None:
            continue

        # Pour chaque vol de ce couple, applique la météo de l'heure d'arrivée prévue
        cursor.execute(
            "SELECT id, crs_arr_time FROM bts_flights WHERE dest = %s AND flight_date = %s AND weather_enriched = FALSE",
            (dest, flight_date)
        )
        flights = cursor.fetchall()

        for f in flights:
            hour = crs_to_hour(f["crs_arr_time"])
            w = hourly.get(hour) or hourly.get(12) or {}
            cursor.execute(
                """
                UPDATE bts_flights SET
                    temperature_c = %s, precipitation_mm = %s, weather_code = %s,
                    wind_speed_kmh = %s, visibility_m = %s, snowfall_cm = %s,
                    weather_enriched = TRUE
                WHERE id = %s
                """,
                (
                    w.get("temperature_c"), w.get("precipitation_mm"), w.get("weather_code"),
                    w.get("wind_speed_kmh"), w.get("visibility_m"), w.get("snowfall_cm"),
                    f["id"],
                )
            )
        conn.commit()
        enriched_couples += 1
        if enriched_couples % 50 == 0:
            log.info(f"  {enriched_couples}/{len(couples)} couples traités")

    cursor.close()
    conn.close()
    log.info(f"Enrichissement météo terminé : {enriched_couples} couples.")


if __name__ == "__main__":
    run()
