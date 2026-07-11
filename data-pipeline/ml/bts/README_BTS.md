# Pipeline d'entraînement rigoureux — données réelles BTS

Ce dossier remplace l'approche "label Google + météo 2025 désalignée" par un
entraînement méthodologiquement correct sur des données réelles.

## Principe

| Élément | Avant (Google) | Maintenant (BTS) |
|---|---|---|
| Vols | Offres 2026 (futures) | Vols réels effectués 2025 |
| Label | Statistique Google "souvent en retard" | Retard réel observé (ArrDelayMinutes > 15 OU annulé) |
| Météo | 2025, désalignée du label | 2025, MÊME jour que le vol (causal) |
| Cohérence | Mélange temporel | Tout sur 2025, aligné |

Le modèle entraîné sur ce dataset (2025 réel) est ensuite **appliqué** aux vols
2026 de SerpAPI pour le front-end (inférence dans main.py).

## Périmètre

- Période : mai, juin, juillet 2025 (trimestre estival, aligné avec juin 2026)
- Vols : ceux qui ARRIVENT dans un aéroport US d'une ville Coupe du Monde
- Label : `is_delayed = 1` si retard arrivée > 15 min OU vol annulé
- Météo : conditions réelles à l'aéroport d'arrivée, jour du vol

## Étapes

### 1. Télécharger les données BTS (manuel — réseau bloqué dans Docker)

Le domaine transtats.bts.gov n'est pas autorisé depuis les conteneurs.
Télécharge les 3 fichiers à la main depuis ton navigateur :

- https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_5.zip
- https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_6.zip
- https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_7.zip

Renomme-les et place-les dans `data-pipeline/data/bts_raw/` :
- `bts_2025_5.zip`
- `bts_2025_6.zip`
- `bts_2025_7.zip`

(Chaque zip fait ~25-50 Mo. Le téléchargement peut être lent, c'est normal.)

### 2. Charger en base (filtre Coupe du Monde + calcul du label)

```bash
docker compose run --rm ml python bts/download_bts.py --from-local
```

Lit les zip locaux, garde les vols arrivant dans tes villes, calcule is_delayed,
insère dans la table BTS_FLIGHTS. Tu verras le taux de retard réel à la fin.

### 3. Enrichir avec la météo réelle du jour

```bash
docker compose run --rm ml python bts/enrich_bts_weather.py
```

Récupère la météo Open-Meteo du jour exact de chaque vol à l'aéroport d'arrivée.
Optimisé : un appel par couple (aéroport, date) unique.

### 4. Construire le dataset d'entraînement

```bash
docker compose run --rm ml python bts/build_training_set_bts.py
```

Écrase `training_set.parquet` et `category_mappings.json` avec les données réelles.

### 5. Entraîner (script train.py inchangé)

```bash
docker compose run --rm ml python train.py
```

Mêmes features, même MLflow. Mais cette fois le modèle apprend de vrais retards.

## Notes méthodologiques (pour le rapport)

- **Distance comme proxy de durée** : le BTS ne nous donne pas le temps de vol
  dans les colonnes chargées, on dérive `duration` de la distance. Approximation
  documentée. On pourrait charger CRSElapsedTime pour être exact.

- **Prix absent** : le BTS ne contient pas les prix. La feature `price` est mise
  à une constante neutre — le modèle l'ignore. C'est honnête : on ne dispose pas
  du prix pour des vols passés. Alternative : retirer price des features.

- **Pas de notion is_best / layover** : propres à SerpAPI, neutralisées (0) pour
  le BTS (vols directs). Cohérent.

- **Volume** : un seul mois de BTS sur tes aéroports = plusieurs milliers de vols,
  bien plus que les 246 de l'approche Google. Statistiquement bien plus solide.

- **Split temporel possible** : pour une évaluation honnête, entraîner sur
  mai-juin et tester sur juillet (futur jamais vu). À configurer dans train.py.
