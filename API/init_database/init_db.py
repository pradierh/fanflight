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


cursor.execute('''
               
    CREATE TABLE IF NOT EXISTS DIM_CITY (
    ID_CITY SERIAL PRIMARY KEY,
    CITY VARCHAR(30) NOT NULL UNIQUE,
    COUNTRY VARCHAR(30) NOT NULL);
               ''')

cursor.execute('''

    CREATE TABLE IF NOT EXISTS DIM_AIRPORT(
    ID_AIRPORT SERIAL PRIMARY KEY,
    IATA_CODE VARCHAR(10) NOT NULL UNIQUE,
    NAME VARCHAR(30) NOT NULL,
    ID_CITY INTEGER REFERENCES DIM_CITY(ID_CITY)
);
               ''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS DIM_TEAM (
        ID_TEAM SERIAL PRIMARY KEY,
        TEAM_NAME VARCHAR(50) NOT NULL UNIQUE,
        TEAM_CODE VARCHAR(3) NOT NULL,
        FLAG_EMOJI VARCHAR(10) DEFAULT '🏳️'
    );
''')


cursor.execute('''
               
    CREATE TABLE IF NOT EXISTS FACT_MATCHS (
    MATCH_ID SERIAL PRIMARY KEY,
    MATCH_DATE TIMESTAMP NOT NULL,
    ID_TEAM_A INTEGER REFERENCES DIM_TEAM(ID_TEAM),
    ID_TEAM_B INTEGER REFERENCES DIM_TEAM(ID_TEAM),
    STAGE VARCHAR(30) NOT NULL,
    ID_CITY INTEGER REFERENCES DIM_CITY(ID_CITY),
    CONSTRAINT unique_match_per_location_time UNIQUE (MATCH_DATE, ID_CITY)
);
               ''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS STG_FLIGHT (
    journey_sk VARCHAR(32),
    flight_sk VARCHAR(32), 
    departure_airport_id VARCHAR(10),
    departure_airport_time TIMESTAMP,
    arrival_airport_id VARCHAR(10),
    arrival_airport_time TIMESTAMP,
    duration INTEGER,
    layover_duration INTEGER,
    total_journey_duration INTEGER,
    price DECIMAL(10, 2),
    airline VARCHAR(100),
    airline_logo TEXT,
    type VARCHAR(20),
    is_best BOOLEAN,
    pos INTEGER           
    
);
               ''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS FACT_FLIGHT (
    flight_sk VARCHAR(32) PRIMARY KEY,
    journey_sk VARCHAR(32), 
    departure_airport_id VARCHAR(10),
    departure_airport_time TIMESTAMP,
    arrival_airport_id VARCHAR(10),
    arrival_airport_time TIMESTAMP,
    duration INTEGER,
    layover_duration INTEGER,
    total_journey_duration INTEGER,
    price DECIMAL(10, 2),
    airline VARCHAR(100),
    airline_logo TEXT,
    type VARCHAR(20),
    is_best BOOLEAN,
    pos INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
               ''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS FLIGHTS_RAW (
    id SERIAL PRIMARY KEY, 
    json_data JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
               ''')

conn.commit()
cursor.close()
conn.close()