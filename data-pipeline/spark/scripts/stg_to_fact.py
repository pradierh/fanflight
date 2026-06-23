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
    job_id = int(job_id)

    print(f"job_id converti : {job_id}")
    cursor = conn.cursor()

    cursor.execute(
        '''
            INSERT INTO fact_flight (
                                    flight_sk, journey_sk, departure_airport_code, departure_airport_time, 
                                    arrival_airport_code, arrival_airport_time, duration, flight_number, layover_duration, total_journey_duration,
                                    price, airline, airline_logo, type, is_best, pos, updated_at
                                    )
            SELECT 
                flight_sk, journey_sk, departure_airport_code, departure_airport_time, 
                arrival_airport_code, arrival_airport_time, duration, flight_number, layover_duration, total_journey_duration,
                price, airline, airline_logo, type, is_best, pos, CURRENT_TIMESTAMP
            FROM stg_flight
            ON CONFLICT (flight_sk) 
            DO UPDATE SET 
                price = EXCLUDED.price,
                departure_airport_time = EXCLUDED.departure_airport_time, 
                updated_at = CURRENT_TIMESTAMP;
            '''
    )

    cursor.execute(
        "UPDATE flights_raw SET processed = True WHERE id = %s", 
        (job_id,))

    conn.commit()
    cursor.close()
    conn.close()
