# 1. On part d'une image Python légère officielle
FROM python:3.11-slim

# 2. On définit le dossier de travail dans le conteneur
WORKDIR /app

# 3. On installe les dépendances système nécessaires pour compiler psycopg2 (liaison Postgres)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. On copie le fichier des dépendances Python et on les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. On copie tout le reste du code de notre API (le dossier app/)
COPY . .

# 6. On expose le port 8000 (le port par défaut de FastAPI)
EXPOSE 8000

# 7. La commande pour lancer le serveur FastAPI avec Uvicorn + les init_db
ENTRYPOINT ["bash", "/app/entrypoint.sh"]