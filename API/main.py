import os
from datetime import timedelta
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json
from collections import defaultdict
import pandas as pd
from prometheus_fastapi_instrumentator import Instrumentator
import logging
from pydantic import BaseModel
from typing import Optional, List


app = FastAPI(title="API de Vols - Coupe du Monde 2026")
Instrumentator().instrument(app).expose(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alertmanager-webhook")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Autorise front Next.js
    allow_credentials=True,
    allow_methods=["*"], # Autorise tous les verbes (GET, POST, etc.)
    allow_headers=["*"], # Autorise tous les headers
)

API_KEY = os.getenv("API_KEY_SERAPI")

class Alert(BaseModel):
    status: str
    labels: dict
    annotations: dict
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None


class AlertmanagerPayload(BaseModel):
    version: str
    groupKey: str
    status: str
    receiver: str
    alerts: List[Alert]

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "airline_data"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password_test"),
        cursor_factory=RealDictCursor
    )

def check_flight_db(cursor, departure_city, arrival_city, match_date_exact):
    flights_query = """
    WITH CTE_DEPARTURE_FLIGHT as(

        select
            journey_sk
        from
            FACT_FLIGHT f
        JOIN
            DIM_AIRPORT dep_a ON f.departure_airport_code = dep_a.iata_code
        JOIN
            DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
        WHERE 
            LOWER(dep_c.city) = LOWER(%s) 
        and f.pos = 0
        )

        , CTE_ARRIVAL_FLIGHT as (

        select
            journey_sk
        from
            fact_flight f
        JOIN
            DIM_AIRPORT arr_a ON f.arrival_airport_code = arr_a.iata_code
        JOIN
            DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
        WHERE 
            LOWER(arr_c.city) = LOWER(%s)
        AND f.pos = (
                SELECT MAX(pos) FROM fact_flight f2 
                WHERE f2.journey_sk = f.journey_sk
                )
        AND f.arrival_airport_time BETWEEN (%s::date - INTERVAL '3 days') AND (%s - INTERVAL '5 hours')
        )

        , UNIONED as (
        
        select 
            df.journey_sk
        from
            CTE_DEPARTURE_FLIGHT df
        join 
            CTE_ARRIVAL_FLIGHT af on df.journey_sk = af.journey_sk
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
                f.airline,
                f.is_best,
                f.pos
            FROM
                FACT_FLIGHT f
            join
                UNIONED u on f.journey_sk = u.journey_sk
            JOIN
                DIM_AIRPORT dep_a ON f.departure_airport_code = dep_a.iata_code
            JOIN
                DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
            JOIN
                DIM_AIRPORT arr_a ON f.arrival_airport_code = arr_a.iata_code
            JOIN 
                DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
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
        last = segments[-1]

        flights.append({
            'journey_sk': journey_sk,
            'price': first['price'],
            'airline': first['airline'],
            'is_best': first['is_best'],
            'total_duration': first['total_journey_duration'],
            'departure_airport_code': first['departure_airport_code'],
            'departure_airport_time': str(first['departure_airport_time']),
            'departure_city': first['departure_city'],
            'arrival_airport_code': last['arrival_airport_code'],
            'arrival_airport_time': str(last['arrival_airport_time']),
            'arrival_city': last['arrival_city'],
            'nb_escales': len(segments) - 1,
            'segments': segments
        })

    return flights

def get_flights_api(cursor, conn, departure_city, arrival_city, match_date_exact):

    # --- ÉTAPE A : Récupérer les codes IATA des aéroports pour les deux villes ---
            # Pour la ville de départ
    cursor.execute("""
                SELECT 
                        iata_code
                FROM 
                        dim_airport a 
                JOIN 
                        dim_city c ON a.id_city = c.id_city
                WHERE 
                        trim(lower(c.city)) = trim(lower(%s))
            """, (departure_city,))

    aeroports_depart = cursor.fetchall() # Renvoie une liste (ex: [{'iata_code': 'CDG'}, {'iata_code': 'ORY'}])
            
            # Pour la ville d'arrivée
    cursor.execute("""
                SELECT 
                        iata_code
                FROM 
                        dim_airport a 
                JOIN 
                        dim_city c ON a.id_city = c.id_city
                WHERE 
                        trim(lower(c.city)) = trim(lower(%s))
            """, (arrival_city,))

    aeroports_arrivee = cursor.fetchall()

            # Sécurité : Si on ne connaît pas les aéroports de ces villes dans notre DIM_AIRPORT
    if not aeroports_depart or not aeroports_arrivee:
            raise HTTPException(
                status_code=400, 
                detail="Impossible de trouver les codes aéroports (IATA) pour ces villes dans le dictionnaire."
            )
            

    all_flights_raw = []
    job_ids = []
            # On boucle sur les aéroports trouvé pour chaque ville (ex: 'CDG' et 'JFK')
    for aero_dep in aeroports_depart:
        code_iata_depart = aero_dep['iata_code'] # (ou aero_dep[0] si cursor normal)
                
                # 2. Boucle sur les aéroports d'arrivée
        for aero_arr in aeroports_arrivee:
            code_iata_arrivee = aero_arr['iata_code']

            for day in range(3): #on fait un appel sur les 3 jours avant le macths
                        
                date_vol = (match_date_exact - timedelta(days= day + 1)).date()
                params = {                        
                "engine": "google_flights",
                "type": "2",
                "departure_id": code_iata_depart,
                "arrival_id": code_iata_arrivee,                    
                "outbound_date": date_vol,
                "currency": "USD",
                "hl": "en",
                "gl": "us",
                "no_cache": 'false',
                "api_key": API_KEY
                }

                try:
                    response = requests.get("https://serpapi.com/search", params=params)

                    if response.status_code == 200:
                        data = response.json()
                        print(data)
                        if 'best_flights' in data or 'other_flights' in data:
                        
                            all_flights_raw.append(data)
                        else:
                            print(f"Pas de vols pour {code_iata_depart} → {code_iata_arrivee}")
                        
                      
                except requests.exceptions.RequestException:
                    print(f"Erreur API pour {code_iata_depart} -> {code_iata_arrivee}")
   
    if all_flights_raw:
        job_id = insert_raw_flights(cursor, conn, all_flights_raw)  
        job_ids.append(job_id)
         
    return job_ids
                             
def insert_raw_flights(cursor, conn, raw_flight):

    query = "INSERT INTO flights_raw (json_data) VALUES (%s) RETURNING id;"

    cursor.execute(query, (json.dumps(raw_flight),))
    
    # On récupère l'ID
    job_id = cursor.fetchone()['id']
    
    cursor.execute("SELECT pg_notify('new_flight', %s)", (str(job_id),))

    # On valide la transaction
    conn.commit()
    
    return job_id

def wait_to_spark(cursor, job_id):

    start = time.time()
    timeout = 90
    while True:

        if time.time() - start > timeout:  # si ça fait plus de 120s
            raise Exception("Timeout")
        
        cursor.execute(
            "SELECT bool_and(processed) as is_done FROM flights_raw WHERE id = ANY(%s)", (job_id,)
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

    rows = cursor.fetchall()

    unknown_iata = []
    for row in rows:
        unknown_iata.append(row['iata_code'])

    if not unknown_iata:
        return
    
    airports_csv = pd.read_csv('/opt/data/raw_data/airport-codes.csv')

    for iata in unknown_iata:
        result = airports_csv[airports_csv['iata_code'] == iata]

        if not result.empty:
            row = result.iloc[0]
            city = str(row['municipality']).strip().title()
            country = str(row['iso_country']).strip().upper()
            name = str(row['name']).strip().lower()
        else:
            city, country, name = 'Unknown', 'Unknown', iata          # Fallback si pas dans le csv

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

@app.get("/api/flights/{match_id}")
def get_flights(match_id: int, departure_city: str):

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. On récupère les infos du match (La date et la ville de destination)
        match_query = """
            SELECT m.MATCH_DATE, c.CITY as arrival_city
            FROM FACT_MATCHS m
            JOIN DIM_CITY c ON m.ID_CITY = c.ID_CITY
            WHERE m.MATCH_ID = %s
        """

        cursor.execute(match_query, (match_id,))

        match_info = cursor.fetchone()
        
        match_date_exact = match_info['match_date']
        print(departure_city)
        print(match_info['arrival_city'])
        flights = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)

        if flights:
            
            cursor.close()
            conn.close()

            return {
            "meta": {
                "match_id": match_id,
                "destination_city": match_info['arrival_city'],
                "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                "results_count": len(flights)
            },
            "flights": flights
            }
        
        if not flights:

            job_ids = get_flights_api(cursor, conn, departure_city, match_info['arrival_city'], match_date_exact)

            if not job_ids:
                  # ← aucun vol trouvé
                return {
                    "meta": {
                    "match_id": match_id,
                    "destination_city": match_info['arrival_city'],
                    "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                    "results_count": len(flights)
                },
                    "flights": []}

            wait_to_spark(cursor,job_ids)

            enrich_airports(cursor, conn)

            flights = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)


            cursor.close()
            conn.close()

            return {
                "meta": {
                    "match_id": match_id,
                    "destination_city": match_info['arrival_city'],
                    "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                    "results_count": len(flights)
                },
                "flights": flights
                }
    except Exception as e:
        # Import de traceback pour afficher l'erreur complète dans ton terminal
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/matches")
def get_matches():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
	            m.match_id,
	            m.match_date,
	            m.id_team_a,
	            ta.team_name as name_team_a,
	            ta.flag as flag_team_a,
	            m.id_team_b,
	            tb.team_name as name_team_b,
	            tb.flag as flag_team_b,
	            m.stage,
	            c.city as city_name

	        FROM FACT_MATCHS m

	        JOIN DIM_TEAM ta on m.id_team_a = ta.id_team

	        JOIN DIM_TEAM tb on m.id_team_b= tb.id_team

	        JOIN DIM_CITY c ON m.id_city = c.id_city

	        ORDER BY m.match_date ASC;
    """)
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    return matches

@app.get("/api/teams")
def get_teams():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
                team_name, team_code, flag
        from
                DIM_TEAM;
    """)
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return teams

@app.get("/api/cities")
def get_cities():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
                c.id_city,
                c.city,
                c.country,
                c.flag,
                array_agg(a.iata_code) as airport_codes
        from
                DIM_CITY c
        LEFT JOIN 
                DIM_AIRPORT a ON c.id_city = a.id_city
        WHERE c.is_host_city = TRUE
        GROUP BY c.id_city, c.city, c.country
        ORDER BY c.city ASC;
    """)
    cities = cursor.fetchall()
    cursor.close()
    conn.close()
    return cities

@app.post("/webhooks/alertmanager")
async def handle_alertmanager_webhook(payload: AlertmanagerPayload):
    for alert in payload.alerts:
        alertname = alert.labels.get("alertname")
        service = alert.labels.get("service")
        severity = alert.labels.get("severity")

        if alert.status != "firing":
            logger.info(f"Alerte résolue: {alertname} ({service})")
            continue

        logger.warning(
            f"Alerte active: {alertname} | service={service} | severity={severity} "
            f"| résumé: {alert.annotations.get('summary')}"
        )
        # TODO: brancher une vraie remédiation ici plus tard

    return {"status": "processed", "count": len(payload.alerts)}


@app.get("/api/test")
def get_test():

    conn = get_db_connection()
    cursor = conn.cursor()
         
    query_test = """SELECT * from fact_flight;"""
    cursor.execute(query_test)
    return cursor.fetchall()
    
