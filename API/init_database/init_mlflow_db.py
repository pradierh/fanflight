"""
init_mlflow_db.py
-----------------
Crée la base de données `mlflow_db` sur l'instance Postgres si elle n'existe pas.
MLflow l'utilise comme backend store (expériences, runs, métriques, registry).

À lancer une fois avant le premier démarrage de MLflow, ou à intégrer dans
l'entrypoint de l'API qui tourne déjà au boot.

Usage :
    docker compose run --rm ml python init_mlflow_db.py
"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connexion à la base par défaut "postgres" pour pouvoir créer une nouvelle base
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "db"),
    port=os.getenv("DB_PORT", "5432"),
    database="postgres",  # base d'admin par défaut
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "password_test"),
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # CREATE DATABASE hors transaction
cursor = conn.cursor()

# Vérifie l'existence avant de créer
cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'mlflow_db';")
exists = cursor.fetchone()

if not exists:
    cursor.execute("CREATE DATABASE mlflow_db;")
    print("Base 'mlflow_db' créée.")
else:
    print("Base 'mlflow_db' déjà existante — rien à faire.")

cursor.close()
conn.close()
