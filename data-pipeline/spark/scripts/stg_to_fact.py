import psycopg2
import os

def stg_to_fact_flight(job_id):

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    cursor = conn.cursor()

    cursor.execute(
        '''
            INSERT INTO fact_flight (
                                    flight_sk, journey_sk, departure_airport_id, departure_airport_time, 
                                    arrival_airport_id, arrival_airport_time, duration, layover_duration, total_journey_duration,
                                    price, airline, airline_logo, type, is_best, pos
                                    )
            SELECT 
                flight_sk, journey_sk, departure_airport_id, departure_airport_time, 
                arrival_airport_id, arrival_airport_time, duration, layover_duration, total_journey_duration,
                price, airline, airline_logo, type, is_best, pos
            FROM stg_flight
            ON CONFLICT (flight_sk) 
            DO UPDATE SET 
                price = EXCLUDED.price,
                departure_airport_time = EXCLUDED.departure_airport_time, -- Nom corrigé
                updated_at = CURRENT_TIMESTAMP;
            '''
    )

    cursor.execute(
        "UPDATE flights_raw SET processed = True WHERE id = %s", 
        (job_id,))

    conn.commit()
    cursor.close()
    conn.close()
