import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

cursor = conn.cursor()

# ------------------------------------------------------------------
# DIMENSIONS
# ------------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS DIM_CITY (
        ID_CITY  SERIAL PRIMARY KEY,
        CITY     VARCHAR(30) NOT NULL UNIQUE,
        COUNTRY  VARCHAR(30) NOT NULL
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS DIM_AIRPORT (
        ID_AIRPORT SERIAL PRIMARY KEY,
        IATA_CODE  VARCHAR(10)    NOT NULL UNIQUE,
        NAME       VARCHAR(50)    NOT NULL,
        ID_CITY    INTEGER        REFERENCES DIM_CITY(ID_CITY),
        LATITUDE   DECIMAL(9, 6),
        LONGITUDE  DECIMAL(9, 6)
    );
""")

# ------------------------------------------------------------------
# FAITS MATCHS
# ------------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS FACT_MATCHS (
        MATCH_ID   SERIAL PRIMARY KEY,
        MATCH_DATE TIMESTAMP    NOT NULL,
        TEAM_A     VARCHAR(30)  NOT NULL,
        TEAM_B     VARCHAR(30)  NOT NULL,
        STAGE      VARCHAR(30)  NOT NULL,
        ID_CITY    INTEGER      REFERENCES DIM_CITY(ID_CITY),
        CONSTRAINT unique_match_per_location_time UNIQUE (MATCH_DATE, ID_CITY)
    );
""")

# ------------------------------------------------------------------
# VOLS — staging + fait
# ------------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS STG_FLIGHT (
        journey_sk             VARCHAR(32),
        flight_sk              VARCHAR(32),
        departure_airport_id   VARCHAR(10),
        departure_airport_time TIMESTAMP,
        arrival_airport_id     VARCHAR(10),
        arrival_airport_time   TIMESTAMP,
        duration               INTEGER,
        layover_duration       INTEGER,
        total_journey_duration INTEGER,
        price                  DECIMAL(10, 2),
        airline                VARCHAR(100),
        airline_logo           TEXT,
        type                   VARCHAR(20),
        is_best                BOOLEAN,
        pos                    INTEGER,
        is_delayed             BOOLEAN DEFAULT FALSE
    );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS FACT_FLIGHT (
        flight_sk              VARCHAR(32)   PRIMARY KEY,
        journey_sk             VARCHAR(32),
        departure_airport_id   VARCHAR(10),
        departure_airport_time TIMESTAMP,
        arrival_airport_id     VARCHAR(10),
        arrival_airport_time   TIMESTAMP,
        duration               INTEGER,
        layover_duration       INTEGER,
        total_journey_duration INTEGER,
        price                  DECIMAL(10, 2),
        airline                VARCHAR(100),
        airline_logo           TEXT,
        type                   VARCHAR(20),
        is_best                BOOLEAN,
        pos                    INTEGER,
        is_delayed             BOOLEAN DEFAULT FALSE,
        created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

# ------------------------------------------------------------------
# MÉTÉO — enrichissement par vol (table séparée, jointure sur flight_sk)
# Stocke les conditions météo à l'aéroport de départ à l'heure du vol.
# Données historiques année N-1 via Open-Meteo archive API.
# ------------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS FACT_FLIGHT_WEATHER (
        flight_sk              VARCHAR(32) PRIMARY KEY REFERENCES FACT_FLIGHT(flight_sk),
        departure_airport_id   VARCHAR(10),
        weather_date           DATE,
        weather_hour           INTEGER,
        temperature_c          DECIMAL(5, 2),
        precipitation_mm       DECIMAL(6, 2),
        weather_code           INTEGER,
        wind_speed_kmh         DECIMAL(6, 2),
        visibility_m           DECIMAL(10, 2),
        snowfall_cm            DECIMAL(6, 2),
        fetched_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

# ------------------------------------------------------------------
# BUFFER TRAITEMENT SPARK
# ------------------------------------------------------------------

cursor.execute("""
    CREATE TABLE IF NOT EXISTS FLIGHTS_RAW (
        id         SERIAL PRIMARY KEY,
        json_data  JSONB,
        processed  BOOLEAN   DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

conn.commit()
cursor.close()
conn.close()

print("init_db OK — toutes les tables créées.")
