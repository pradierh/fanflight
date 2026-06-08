# spark_listener.py
import psycopg2
import psycopg2.extensions
import select
import subprocess
import os

conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()
cursor.execute("LISTEN new_flight;")


while True:
    try:
        select.select([conn], [], [])
        conn.poll()

        for notify in conn.notifies:
            job_id = notify.payload
            subprocess.Popen([
                "/opt/spark/bin/spark-submit",
                "--master", "spark://spark-master:7077",
                "/opt/spark/scripts/process_flight.py",
                job_id
            ])

        conn.notifies.clear()  
    except Exception as e:
        print(f"Erreur : {e}")


