import os
from datetime import datetime, timedelta
import time
from fastapi import FastAPI, HTTPException
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import json


app = FastAPI(title="API de Vols - Coupe du Monde 2026")

API_KEY = os.getenv("API_KEY_SERAPI")

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
            DIM_AIRPORT dep_a ON f.departure_airport_id = dep_a.iata_code
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
            DIM_AIRPORT arr_a ON f.arrival_airport_id = arr_a.iata_code
        JOIN
            DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
        WHERE 
            LOWER(arr_c.city) = LOWER(%s) 
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
                f.departure_airport_id,
                f.departure_airport_time,
                arr_c.city as arrival_city,
                f.arrival_airport_id,
                f.arrival_airport_time,
                f.price,
                f.airline
            FROM
                FACT_FLIGHT f
            join
                UNIONED u on f.journey_sk = u.journey_sk
            JOIN
                DIM_AIRPORT dep_a ON f.departure_airport_id = dep_a.iata_code
            JOIN
                DIM_CITY dep_c ON dep_a.id_city = dep_c.id_city
            JOIN
                DIM_AIRPORT arr_a ON f.arrival_airport_id = arr_a.iata_code
            JOIN 
                DIM_CITY arr_c ON arr_a.id_city = arr_c.id_city
            WHERE
                f.arrival_airport_time BETWEEN (%s::date - INTERVAL '3 days') AND (%s - INTERVAL '5 hours')
            ORDER BY journey_sk, departure_airport_time asc;
        """
        
    cursor.execute(flights_query, (departure_city, arrival_city, match_date_exact, match_date_exact))
    return cursor.fetchall()

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
            # On boucle sur les aéroports trouvé pour chaque ville (ex: 'CDG' et 'JFK')
    for aero_dep in aeroports_depart:
        code_iata_depart = aero_dep['iata_code'] # (ou aero_dep[0] si cursor normal)
                
                # 2. Boucle sur les aéroports d'arrivée
        for aero_arr in aeroports_arrivee:
            code_iata_arrivee = aero_arr['iata_code']

            for day in range(2): #on fait un appel sur les 3 jours avant le macths
                        
                date_vol = (match_date_exact - timedelta(days= day + 1)).date()
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
                        data = response.json()
                        all_flights_raw.append(data)
                        
                      
                except requests.exceptions.RequestException:
                    print(f"Erreur API pour {code_iata_depart} -> {code_iata_arrivee}")

    print(all_flights_raw)      

    job_id = insert_raw_flights(cursor, conn, all_flights_raw)  
         
    return job_id
                             
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
    timeout = 120
    while True:

        if time.time() - start > timeout:  # si ça fait plus de 120s
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
        vols = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)

        if vols:
            
            cursor.close()
            conn.close()

            return {
            "meta": {
                "match_id": match_id,
                "destination_city": match_info['arrival_city'],
                "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                "results_count": len(vols)
            },
            "flights": vols
            }
        
        if not vols:

            job_id = get_flights_api(cursor, conn, departure_city, match_info['arrival_city'], match_date_exact)

            wait_to_spark(cursor,job_id)

            vols = check_flight_db(cursor, departure_city, match_info['arrival_city'], match_date_exact)


        cursor.close()
        conn.close()

        return {
            "meta": {
                "match_id": match_id,
                "departure_city": departure_city,
                "destination_city": match_info['arrival_city'],
                "match_date_actual": match_date_exact.strftime("%Y-%m-%d %H:%M"),
                "results_count": len(vols)
            },
            "flights": vols
        }

    except Exception as e:
        # Import de traceback pour afficher l'erreur complète dans ton terminal
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))