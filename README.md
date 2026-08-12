# Fanflight - Prediction de retard de vols (Coupe du Monde 2026)

Systeme complet de data engineering et de machine learning qui predit, pour
chaque vol amenant un supporter a un match, une probabilite de retard affichee
dans le front.

## Architecture en deux flux

Le projet separe proprement l'entrainement (passe observe) de l'inference
(futur predit) :

| Flux | Source | Role |
|---|---|---|
| Entrainement | BTS 2025 (vols US reels) | Apprendre les patterns de retard sur de vraies donnees |
| Application / Inference | SerpAPI (vols 2026) | Fournir les vols au front et predire leur retard |

- Entrainement : vols reellement effectues (mai-juin-juillet 2025, source BTS),
  retard reellement observe (ArrDelayMinutes superieur a 15 min OU vol annule),
  meteo reelle du jour du vol (Open-Meteo). Coherence temporelle complete.
- Inference : l'API charge le modele entraine et score en temps reel les vols
  2026 renvoyes par SerpAPI.

## Structure du projet

```
fanflight/
├── docker-compose.yml             # source de verite unique (local ET prod)
├── docker-compose.override.yml    # charge auto en local : build + bind-mounts source
├── .env
├── API/
│   ├── main.py                    # API + chargement modele + prediction + cache
│   ├── feature_builder.py         # encodage features (partage)
│   ├── requirements.txt           # inclut mlflow, xgboost, pandas
│   └── init_database/
│       ├── init_db.py
│       └── load_static_data.py
├── frontend/
├── documentation/
└── data-pipeline/
    ├── data/
    │   ├── bts_raw/               # zips BTS telecharges a la main
    │   └── raw_data/             # cache reponses SerpAPI (replay_job)
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

### 1. Demarrer l'infra
```bash
docker compose up -d
docker compose ps   # attendre que postgres soit healthy
```
Lance : Postgres, API FastAPI, frontend, MLflow, conteneur ML (dormant).
`docker-compose.override.yml` est charge automatiquement (build depuis le
code source + montage `./API`, `./data-pipeline/ml` pour l'auto-reload).

Pour tester en plus la pile de monitoring (Prometheus, Grafana, Alertmanager,
exporters) et Watchtower, memes services qu'en production :
```bash
docker compose --profile prod up -d
```

### 2. Creer la base MLflow (une seule fois)
```bash
docker compose run --rm ml python init_mlflow_db.py
docker compose restart mlflow
```
UI MLflow : http://localhost:5000

## Entrainement sur donnees reelles BTS

### 3. Telecharger les donnees BTS (manuel)
Le domaine transtats.bts.gov est bloque par le reseau Docker. Telecharge a la
main les trois fichiers :
- transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_5.zip
- ...2025_6.zip
- ...2025_7.zip

Renomme en bts_2025_5.zip, bts_2025_6.zip, bts_2025_7.zip et place dans
data-pipeline/data/bts_raw/.

### 4. Charger, enrichir, construire
```bash
docker compose run --rm ml python bts/download_bts.py --from-local
docker compose run --rm ml python bts/enrich_bts_weather.py
docker compose run --rm ml python bts/build_training_set_bts.py
```

### 5. Entrainer (XGBoost et reseau de neurones)
```bash
docker compose run --rm ml python train.py
```
Compare les deux modeles, versionne dans MLflow, promeut le meilleur en
Production.

## Brancher l'API sur le modele (serving)

### 6. Rebuild l'API et tester
```bash
docker compose up -d --build backend-api
curl "http://localhost:8000/health"          # model_loaded: true attendu
curl "http://localhost:8000/api/flights/1?departure_city=Miami"
```
Chaque vol renvoye contient delay_probability, delay_prediction, model_used.

## Monitoring de derive
```bash
docker compose run --rm ml python drift_monitor.py
```
PSI et KS-test entre la reference et un nouveau batch (simule si non fourni).

## Fonctionnement de la prediction

Au demarrage, l'API charge le meilleur modele depuis MLflow (chargement direct
du booster XGBoost) et le fichier category_mappings.json (encodage des
compagnies et aeroports, identique a l'entrainement).

A chaque appel de /api/flights, pour chaque vol :
1. Les features sont reconstruites via feature_builder (le meme module qu'a
   l'entrainement, garantissant un encodage identique).
2. La meteo est recuperee (voir strategie adaptative ci-dessous).
3. Le modele predit une probabilite de retard entre 0 et 1.

Trois champs sont ajoutes a chaque vol :
- delay_probability : probabilite continue de retard (0 a 1)
- delay_prediction : binarisation au seuil 0.5 (true / false)
- model_used : nom du modele ayant produit la prediction

## Strategie meteo adaptative a l'inference

La meteo utilisee pour predire depend de la proximite du vol :
- Vol dans les 16 jours : prevision meteo REELLE via l'API forecast Open-Meteo,
  a l'aeroport d'arrivee (coherent avec l'entrainement BTS).
- Vol plus lointain : repli sur FACT_FLIGHT_WEATHER (approximation saisonniere
  annee N-1).
- Aucune donnee disponible : valeurs par defaut neutres.

Le cas d'usage vise est un utilisateur consultant a l'approche du match, donc
dans la fenetre de prevision. Note : api.open-meteo.com doit etre joignable
depuis le conteneur backend-api ; sinon le systeme retombe sur le repli en base.

## Cache des trajets (economie de quota SerpAPI)

Pour ne jamais reconsommer le quota SerpAPI sur un trajet deja demande, la table
QUERIED_ROUTES enregistre chaque trajet (depart, arrivee, match) interroge, meme
s'il n'a retourne aucun vol.

- Premier appel d'un trajet : lecture base, puis appel SerpAPI si vide, puis
  enregistrement du trajet dans le registre.
- Appels suivants du meme trajet : lecture base uniquement, jamais d'appel API.
- Parametre ?force=true : force un rappel API malgre le registre (tests ou
  rafraichissement volontaire).

Le champ meta.from_cache dans la reponse indique si les donnees proviennent du
cache.

## Resultats actuels 

- Volume : 628 704 vols reels BTS (contre 246 dans l'ancienne approche Google).
- Taux de retard observe : 27,8 % (realiste pour le domestique US estival).
- Performance : XGBoost AUC = 0,728, reseau de neurones AUC = 0,713. Scores
  fiables car calcules sur des dizaines de milliers de vols de test.
- Modele retenu : XGBoost (legerement superieur, classique sur le tabulaire),
  promu en Production et servi par l'API.

## Label et sortie du modele

- Label d'entrainement : is_delayed, binaire (0 ou 1). Un vol est etiquete 1 si
  son retard d'arrivee depasse 15 min OU s'il est annule.
- Sortie du modele a l'inference : delay_probability, probabilite continue entre
  0 et 1, puis delay_prediction (binarisation au seuil 0.5).

C'est le fonctionnement standard d'une classification binaire : on entraine sur
des etiquettes oui/non, le modele produit une probabilite continue.

## Limites assumees 

- Duree derivee de la distance : le BTS charge ne contient pas le temps de vol,
  on l'approxime via la distance. Documente dans build_training_set_bts.py.
- Prix absent du BTS : feature price neutralisee a l'entrainement (constante).
  Le modele s'appuie surtout sur l'heure, la compagnie, la meteo.
- Vols directs uniquement : le BTS ne couvre pas les correspondances, donc
  layover_duration, is_best, pos valent 0 a l'entrainement. A l'inference, les
  vols SerpAPI avec escale sont scores segment par segment.
- Serving par volume partage : les artefacts MLflow sont partages entre
  conteneurs via un volume Docker. En production reelle, on servirait les
  artefacts en HTTP via le serveur MLflow.

## Features utilisees (20)

| Categorie | Features |
|---|---|
| Vol | duration, layover_duration, total_journey_duration, price, pos, is_best |
| Temporel | hour_of_day, day_of_week, is_overnight, has_layover |
| Categoriel | airline, departure_airport_id, arrival_airport_id (encodes via mapping sauvegarde) |
| Meteo | temperature_c, precipitation_mm, weather_code, wind_speed_kmh, visibility_m, snowfall_cm, weather_risk_score |

Label : is_delayed (binaire, retard arrivee superieur a 15 min OU annule)

## Notes d'exploitation

- Arreter sans perdre les donnees : docker compose stop (puis docker compose
  start pour reprendre). Ne jamais utiliser docker compose down -v, qui
  supprime les volumes (base et modele).
- Les modeles et donnees ne sont pas versionnes dans Git (volumes locaux). Un
  clone du depot doit rejouer le pipeline d'entrainement pour regenerer le
  modele sur sa propre machine.
- Fins de ligne : conserver LF (pas CRLF) sur les .sh et .py pour eviter les
  erreurs dans les conteneurs Linux. Un fichier .gitattributes est recommande.
```
