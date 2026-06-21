# Fanflight — Prédiction de retard de vols (Coupe du Monde 2026)

Système complet de data engineering + ML qui prédit, pour chaque vol amenant un
supporter à un match, une **probabilité de retard** affichée dans le front.

## Architecture en deux flux

Le projet sépare proprement l'entraînement (passé observé) de l'inférence (futur prédit) :

| Flux | Source | Rôle |
|---|---|---|
| **Entraînement** | BTS 2025 (vols US réels) | Apprendre les patterns de retard sur de vraies données |
| **Application / Inférence** | SerpAPI (vols 2026) | Fournir les vols au front + prédire leur retard |

- **Entraînement** : vols réellement effectués (mai-juin-juillet 2025, source BTS),
  retard réellement observé (`ArrDelayMinutes > 15` OU vol annulé), météo réelle
  du jour du vol (Open-Meteo). Cohérence temporelle complète.
- **Inférence** : l'API charge le modèle entraîné et score en temps réel les vols
  2026 renvoyés par SerpAPI.

## Structure du projet

```
fanflight/
├── docker-compose.yml
├── .env
├── API/
│   ├── main.py                  # API + chargement modèle + prédiction
│   ├── feature_builder.py       # encodage features (partagé)
│   ├── requirements.txt         # inclut mlflow, xgboost, pandas
│   └── init_database/
│       ├── init_db.py
│       └── load_static_data.py
└── data-pipeline/
    ├── data/
    │   ├── bts_raw/             # zips BTS téléchargés à la main
    │   └── raw_data/           # cache réponses SerpAPI (replay_job)
    ├── spark/scripts/
    │   ├── process_flight.py
    │   ├── spark_listener.py
    │   └── stg_to_fact.py
    └── ml/
        ├── feature_builder.py
        ├── build_training_set.py
        ├── train.py
        ├── drift_monitor.py
        ├── fetch_weather.py
        ├── init_mlflow_db.py
        └── bts/
            ├── download_bts.py
            ├── enrich_bts_weather.py
            ├── build_training_set_bts.py
            └── feature_builder.py
```

## Mise en route

### 1. Démarrer l'infra
```bash
docker compose up -d
docker compose ps   # attendre que postgres soit healthy
```
Lance : Postgres, Spark (master+worker), API FastAPI, MLflow, conteneur ML (dormant).

### 2. Créer la base MLflow (une seule fois)
```bash
docker compose run --rm ml python init_mlflow_db.py
docker compose restart mlflow
```
UI MLflow : http://localhost:5000

## Entraînement sur données réelles BTS

### 3. Télécharger les données BTS (manuel)
Le domaine transtats.bts.gov est bloqué par le réseau Docker. Télécharge à la main :
- transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_5.zip
- ...2025_6.zip
- ...2025_7.zip

Renommer en `bts_2025_5.zip`, `bts_2025_6.zip`, `bts_2025_7.zip`
et placer dans `data-pipeline/data/bts_raw/`.

### 4. Charger, enrichir, construire
```bash
docker compose run --rm ml python bts/download_bts.py --from-local
docker compose run --rm ml python bts/enrich_bts_weather.py
docker compose run --rm ml python bts/build_training_set_bts.py
```

### 5. Entraîner (XGBoost + réseau de neurones)
```bash
docker compose run --rm ml python train.py
```
Compare les deux modèles, versionne dans MLflow, promeut le meilleur en Production.

## Brancher l'API sur le modèle (serving)

### 6. Rebuild l'API et tester
```bash
docker compose up -d --build backend-api
curl "http://localhost:8000/health"          # model_loaded: true attendu
curl "http://localhost:8000/api/flights/1?departure_city=Miami"
```
Chaque vol renvoyé contient `delay_probability`, `delay_prediction`, `model_used`.

## Monitoring de dérive
```bash
docker compose run --rm ml python drift_monitor.py
```
PSI + KS-test entre la référence et un nouveau batch (simulé si non fourni).

## Résultats actuels (à citer dans le rapport)

- **Volume** : 628 704 vols réels BTS (vs 246 dans l'ancienne approche Google).
- **Taux de retard observé** : 27,8 % (réaliste pour le domestique US estival).
- **Performance** : XGBoost AUC = 0,728, réseau de neurones AUC = 0,713.
  Scores fiables car calculés sur des dizaines de milliers de vols de test.
- **Modèle retenu** : XGBoost (légèrement supérieur, classique sur le tabulaire),
  promu en Production et servi par l'API.

## Limites assumées (transparence rapport)

- **Durée dérivée de la distance** : le BTS chargé ne contient pas le temps de
  vol, on l'approxime via la distance. Documenté dans build_training_set_bts.py.
- **Prix absent du BTS** : feature `price` neutralisée à l'entraînement
  (constante). Le modèle s'appuie surtout sur l'heure, la compagnie, la météo.
- **Vols directs uniquement** : le BTS ne couvre pas les correspondances, donc
  `layover_duration`, `is_best`, `pos` = 0 à l'entraînement. À l'inférence, les
  vols SerpAPI avec escale sont scorés segment par segment.
- **Serving par volume partagé** : les artefacts MLflow sont partagés entre
  conteneurs via volume. En production réelle, on servirait les artefacts en
  HTTP via le serveur MLflow.

## Features utilisées (20)

| Catégorie | Features |
|---|---|
| Vol | duration, layover_duration, total_journey_duration, price, pos, is_best |
| Temporel | hour_of_day, day_of_week, is_overnight, has_layover |
| Catégoriel | airline, departure_airport_id, arrival_airport_id (encodés via mapping sauvegardé) |
| Météo | temperature_c, precipitation_mm, weather_code, wind_speed_kmh, visibility_m, snowfall_cm, weather_risk_score |

Label : `is_delayed` (binaire — retard arrivée > 15 min OU annulé)
```
