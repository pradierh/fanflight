# Pipeline ML — Prédiction de retard de vols

Prédit si un vol sera en retard (> 30 min) avec un score de probabilité,
en s'appuyant sur les données Google Flights (champ `often_delayed_by_over_30_min`)
enrichies par la météo historique (Open-Meteo).

## Où placer les fichiers

```
project-root/
├── docker-compose.yml              <- REMPLACE l'ancien
├── .env                            <- ajoute API_KEY_SERAPI
├── API/
│   └── init_database/
│       ├── init_db.py              <- REMPLACE (ajoute is_delayed, lat/lon, table météo)
│       └── load_static_data.py     <- REMPLACE (ajoute les coordonnées aéroports)
└── data-pipeline/
    ├── spark/scripts/
    │   ├── process_flight.py       <- PATCHE (voir patch_process_flight.py)
    │   └── stg_to_fact.py          <- PATCHE (voir patch_process_flight.py)
    └── ml/                         <- NOUVEAU DOSSIER
        ├── Dockerfile              <- (Dockerfile.ml renommé en Dockerfile)
        ├── requirements_ml.txt
        ├── init_mlflow_db.py
        ├── fetch_weather.py
        ├── build_training_set.py
        ├── train.py
        └── drift_monitor.py
```

## Ordre d'exécution

### 1. Démarrer l'infra
```bash
docker compose up --build -d
```
Cela lance : Postgres, Spark (master+worker), API FastAPI, MLflow, et le conteneur ML (dormant).

### 2. Créer la base MLflow (une seule fois)
```bash
docker compose run --rm ml python init_mlflow_db.py
```
MLflow redémarre proprement ensuite. UI accessible sur http://localhost:5000

### 3. Alimenter FACT_FLIGHT
Appelle l'API pour déclencher l'ingestion Spark sur quelques matchs :
```bash
curl "http://localhost:8000/api/flights/1?departure_city=Miami"
curl "http://localhost:8000/api/flights/2?departure_city=Dallas"
# etc. — plus tu fais d'appels, plus ton dataset grandit
```

### 4. Enrichir avec la météo
```bash
docker compose run --rm ml python fetch_weather.py
```

### 5. Construire le dataset d'entraînement
```bash
docker compose run --rm ml python build_training_set.py
```
Génère `data-pipeline/data/training_set.parquet`

### 6. Entraîner et comparer les modèles
```bash
docker compose run --rm ml python train.py
```
Entraîne XGBoost + réseau de neurones, log tout dans MLflow, versionne les modèles.

### 7. Monitorer la dérive
```bash
# Avec un nouveau batch :
docker compose run --rm ml python drift_monitor.py --current /opt/data/new_batch.parquet

# Sans batch (simulation de dérive pour démo) :
docker compose run --rm ml python drift_monitor.py
```

## Points d'attention (à mentionner au rapport)

- **Volume de données** : avec ~268 legs, les scores (AUC ~0.97 en test) sont
  optimistes et instables. La performance n'est fiable qu'avec plus de volume.
  Multiplie les appels API pour grossir le dataset.

- **Label synthétique partiel** : `often_delayed_by_over_30_min` vient de Google
  Flights — c'est une probabilité historique, pas un retard observé sur CE vol.
  C'est honnête et défendable, mais à expliciter.

- **Météo en N-1** : les vols de juin 2026 utilisent la météo de juin 2025 à
  l'aéroport de départ (approximation saisonnière). Documenté dans fetch_weather.py.

- **Déséquilibre** : 34% de retards. Géré par `scale_pos_weight` (XGBoost) et
  `pos_weight` dans la BCE (réseau de neurones). Pas de SMOTE nécessaire.

## Features utilisées

| Catégorie | Features |
|---|---|
| Vol | duration, layover_duration, total_journey_duration, price, pos, is_best |
| Temporel | hour_of_day, day_of_week, is_overnight |
| Catégoriel | airline, departure_airport_id, arrival_airport_id (label-encodés) |
| Météo | temperature_c, precipitation_mm, weather_code, wind_speed_kmh, visibility_m, snowfall_cm, weather_risk_score |

Label : `is_delayed` (binaire)
