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
print("[Listener] En écoute sur le canal 'new_flight' ...")

while True:
    try:
        # Timeout de 5s pour garder la connexion vivante
        if select.select([conn], [], [], 5) == ([], [], []):
            continue
        conn.poll()

        for notify in conn.notifies:
            job_id = notify.payload
            print(f"[Listener] Job reçu : id={job_id}, lancement de spark-submit ...")
            # subprocess.run est BLOQUANT : le job suivant n'est traité
            # qu'une fois celui-ci terminé. Évite la corruption de STG_FLIGHT
            # (mode overwrite) en cas de jobs concurrents.
            subprocess.run([
                "/opt/spark/bin/spark-submit",
                "--master", "spark://spark-master:7077",
                "--driver-class-path", "/opt/spark/jars/postgresql-42.7.2.jar",
                "--jars", "/opt/spark/jars/postgresql-42.7.2.jar",
                "/opt/spark/scripts/process_flight.py",
                job_id
            ], check=True)
            print(f"[Listener] Job id={job_id} terminé.")

        conn.notifies.clear()

    except subprocess.CalledProcessError as e:
        print(f"[Listener] spark-submit a échoué : {e}")
    except Exception as e:
        print(f"[Listener] Erreur : {e}")
