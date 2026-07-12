FROM apache/spark:latest

USER root

# 3. On installe les dépendances système nécessaires pour compiler psycopg2 (liaison Postgres)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. On copie le fichier des dépendances Python et on les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts /opt/spark/scripts
RUN chmod -R 755 /opt/spark/scripts

ADD https://jdbc.postgresql.org/download/postgresql-42.7.2.jar /opt/spark/jars/postgresql-42.7.2.jar
RUN chmod 644 /opt/spark/jars/postgresql-42.7.2.jar

