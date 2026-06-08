import glob
import json
import psycopg2
import os

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="airline_data",
    user="root",
    password="password_test"
)
cursor = conn.cursor()

all_data = []

# Lit tous les fichiers JSON sauvegardés
for file in glob.glob("/app/data/reponse_*.json"):
    with open(file) as f:
        all_data.append(json.load(f))

# Insert en base
cursor.execute(
    "INSERT INTO flights_raw (json_data) VALUES (%s) RETURNING id;",
    (json.dumps(all_data),)
)
job_id = cursor.fetchone()[0]
cursor.execute("SELECT pg_notify('new_flight', %s)", (str(job_id),))
conn.commit()

print(f"✅ Job {job_id} relancé")
cursor.close()
conn.close()