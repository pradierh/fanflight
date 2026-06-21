"""
fetch_weather.py
----------------
Enrichit FACT_FLIGHT avec les données météo historiques (année N-1) via
l'API gratuite Open-Meteo Archive.

Logique :
  - Pour chaque vol dans FACT_FLIGHT sans entrée dans FACT_FLIGHT_WEATHER,
    on récupère les conditions météo à l'aéroport de DÉPART,
    à l'heure locale du vol, pour la même date un an avant.

  - Les coordonnées lat/lon viennent de DIM_AIRPORT (ajoutées dans init_db).

  - Le script est idempotent : il peut être relancé sans dupliquer de données.

Lancer depuis le container backend ou un service dédié :
    python fetch_weather.py

Variables d'environnement requises : DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import time
import logging
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS    = "temperature_2m,precipitation,weather_code,wind_speed_10m,visibility,snowfall"

# Pause entre les appels API pour respecter le rate limit Open-Meteo (10 000 req/jour gratuit)
SLEEP_BETWEEN_CALLS = 0.5  # secondes

# Nombre d'années à remonter pour la météo historique
YEARS_BACK = 1


# ------------------------------------------------------------------
# DB
# ------------------------------------------------------------------

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def fetch_flights_without_weather(cursor):
    """Retourne les vols qui n'ont pas encore de données météo."""
    cursor.execute("""
        SELECT
            f.flight_sk,
            f.departure_airport_id,
            f.departure_airport_time,
            a.latitude,
            a.longitude
        FROM fact_flight f
        JOIN dim_airport a ON f.departure_airport_id = a.iata_code
        LEFT JOIN fact_flight_weather w ON f.flight_sk = w.flight_sk
        WHERE w.flight_sk IS NULL
          AND a.latitude  IS NOT NULL
          AND a.longitude IS NOT NULL
        ORDER BY f.departure_airport_time;
    """)
    return cursor.fetchall()


# ------------------------------------------------------------------
# Open-Meteo
# ------------------------------------------------------------------

def fetch_weather(lat: float, lon: float, date_str: str) -> dict | None:
    """
    Appelle l'API Open-Meteo Archive pour une date donnée (format YYYY-MM-DD).
    Retourne un dict {heure: {variable: valeur}} ou None en cas d'erreur.
    """
    params = {
        "latitude":   lat,
        "longitude":  lon,
        "start_date": date_str,
        "end_date":   date_str,
        "hourly":     HOURLY_VARS,
        "timezone":   "auto",
    }

    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        hourly = data.get("hourly", {})
        times  = hourly.get("time", [])

        # Construit un dict indexé par heure (0–23)
        result = {}
        for i, t in enumerate(times):
            hour = int(t.split("T")[1][:2]) if "T" in t else int(t.split(" ")[1][:2])
            result[hour] = {
                "temperature_c":    hourly.get("temperature_2m",  [None] * 24)[i],
                "precipitation_mm": hourly.get("precipitation",   [None] * 24)[i],
                "weather_code":     hourly.get("weather_code",    [None] * 24)[i],
                "wind_speed_kmh":   hourly.get("wind_speed_10m",  [None] * 24)[i],
                "visibility_m":     hourly.get("visibility",      [None] * 24)[i],
                "snowfall_cm":      hourly.get("snowfall",        [None] * 24)[i],
            }
        return result

    except requests.exceptions.RequestException as e:
        log.warning(f"Open-Meteo error for lat={lat} lon={lon} date={date_str}: {e}")
        return None


def insert_weather(cursor, flight_sk, departure_airport_id, weather_date, hour, weather):
    cursor.execute(
        """
        INSERT INTO fact_flight_weather (
            flight_sk, departure_airport_id,
            weather_date, weather_hour,
            temperature_c, precipitation_mm, weather_code,
            wind_speed_kmh, visibility_m, snowfall_cm
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (flight_sk) DO NOTHING;
        """,
        (
            flight_sk,
            departure_airport_id,
            weather_date,
            hour,
            weather.get("temperature_c"),
            weather.get("precipitation_mm"),
            weather.get("weather_code"),
            weather.get("wind_speed_kmh"),
            weather.get("visibility_m"),
            weather.get("snowfall_cm"),
        ),
    )


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def run():
    conn   = get_conn()
    cursor = conn.cursor()

    flights = fetch_flights_without_weather(cursor)
    log.info(f"{len(flights)} vols à enrichir avec la météo.")

    # Cache par (lat, lon, date) pour éviter les appels en double
    weather_cache: dict[tuple, dict] = {}

    enriched = 0
    failed   = 0

    for flight in flights:
        flight_sk      = flight["flight_sk"]
        iata           = flight["departure_airport_id"]
        dep_time: datetime = flight["departure_airport_time"]
        lat            = float(flight["latitude"])
        lon            = float(flight["longitude"])

        # Date historique : même jour, même heure, N années en arrière
        historical_dt  = dep_time.replace(year=dep_time.year - YEARS_BACK)
        historical_date = historical_dt.strftime("%Y-%m-%d")
        flight_hour     = dep_time.hour

        cache_key = (lat, lon, historical_date)

        if cache_key not in weather_cache:
            log.info(f"  Appel Open-Meteo : {iata} {historical_date}")
            weather_cache[cache_key] = fetch_weather(lat, lon, historical_date)
            time.sleep(SLEEP_BETWEEN_CALLS)

        hourly_data = weather_cache[cache_key]

        if hourly_data is None:
            log.warning(f"  Pas de données météo pour {flight_sk} — ignoré.")
            failed += 1
            continue

        hour_data = hourly_data.get(flight_hour)
        if hour_data is None:
            log.warning(f"  Heure {flight_hour} absente dans la réponse pour {flight_sk}.")
            failed += 1
            continue

        insert_weather(cursor, flight_sk, iata, historical_date, flight_hour, hour_data)
        enriched += 1

        # Commit par batch de 50 pour ne pas garder une transaction longue
        if enriched % 50 == 0:
            conn.commit()
            log.info(f"  Commit intermédiaire — {enriched} vols enrichis.")

    conn.commit()
    cursor.close()
    conn.close()

    log.info(f"fetch_weather terminé : {enriched} enrichis, {failed} échoués.")


if __name__ == "__main__":
    run()
