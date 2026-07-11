"""
feature_builder.py
-------------------
Module PARTAGÉ entre l'entraînement (build_training_set.py) et l'inférence
(API main.py). Son rôle unique : transformer un vol brut en vecteur de features
de façon STRICTEMENT IDENTIQUE des deux côtés.

C'est la pièce qui évite le piège classique du serving ML : si l'encodage des
compagnies ou l'ordre des colonnes diffère entre entraînement et inférence,
les prédictions deviennent du bruit.

Principe :
  - L'ordre des features (FEATURE_COLS) est figé ici, source unique de vérité.
  - Les mappings d'encodage (airline -> code, aéroport -> code) sont calculés
    à l'entraînement, sauvegardés en JSON, puis rechargés à l'inférence.
  - WMO_RISK et les valeurs météo par défaut sont définis une seule fois ici.
"""

import json
from pathlib import Path

import pandas as pd

# ------------------------------------------------------------------
# ORDRE DES FEATURES — source unique de vérité.
# train.py et main.py importent CETTE liste, jamais une copie locale.
# ------------------------------------------------------------------
FEATURE_COLS = [
    # Numériques vol
    "duration", "layover_duration", "total_journey_duration", "price",
    "hour_of_day", "day_of_week", "pos",
    # Flags
    "is_best", "is_overnight", "has_layover",
    # Catégorielles encodées
    "airline_code", "dep_airport_code", "arr_airport_code",
    # Météo
    "temperature_c", "precipitation_mm", "weather_code",
    "wind_speed_kmh", "visibility_m", "snowfall_cm", "weather_risk_score",
]

LABEL_COL = "is_delayed"

# ------------------------------------------------------------------
# Mapping code météo WMO -> score de risque ordinal
# ------------------------------------------------------------------
WMO_RISK = {
    0: 0, 1: 0, 2: 0, 3: 0,
    45: 2, 48: 2,
    51: 1, 53: 1, 55: 2,
    61: 1, 63: 2, 65: 2,
    71: 2, 73: 2, 75: 3,
    80: 1, 81: 2, 82: 2,
    95: 3, 96: 3, 99: 3,
}

# ------------------------------------------------------------------
# Valeurs météo par défaut si une donnée manque à l'inférence
# (mêmes valeurs neutres qu'à l'entraînement)
# ------------------------------------------------------------------
WEATHER_DEFAULTS = {
    "temperature_c": 20.0,
    "precipitation_mm": 0.0,
    "wind_speed_kmh": 10.0,
    "visibility_m": 10000.0,
    "snowfall_cm": 0.0,
    "weather_code": 0,
}


# ==================================================================
# ENCODAGE CATÉGORIEL — sauvegarde / chargement des mappings
# ==================================================================

def build_category_mappings(df: pd.DataFrame) -> dict:
    """
    Calcule les mappings catégorie -> code depuis le dataset d'entraînement.
    Appelé UNE FOIS à l'entraînement, puis sauvegardé.
    """
    return {
        "airline": {v: i for i, v in enumerate(sorted(df["airline"].dropna().unique()))},
        "departure_airport_code": {v: i for i, v in enumerate(sorted(df["departure_airport_code"].dropna().unique()))},
        "arrival_airport_code": {v: i for i, v in enumerate(sorted(df["arrival_airport_code"].dropna().unique()))},
    }


def save_mappings(mappings: dict, path: Path):
    with open(path, "w") as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)


def load_mappings(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def encode_category(value, mapping: dict) -> int:
    """
    Encode une valeur catégorielle avec le mapping sauvegardé.
    Valeur inconnue (compagnie jamais vue à l'entraînement) -> -1.
    """
    return mapping.get(value, -1)


# ==================================================================
# CONSTRUCTION DES FEATURES POUR UN VOL (inférence)
# ==================================================================

def build_features_for_flight(flight: dict, weather: dict | None, mappings: dict) -> dict:
    """
    Transforme un vol unique + sa météo en dict de features prêt pour la prédiction.

    flight : dict avec au minimum
        airline, departure_airport_code, arrival_airport_code,
        duration, layover_duration, total_journey_duration, price,
        is_best, pos, departure_airport_time
    weather : dict météo (temperature_c, precipitation_mm, weather_code,
              wind_speed_kmh, visibility_m, snowfall_cm) ou None
    mappings : mappings d'encodage chargés depuis l'entraînement

    Retourne un dict {feature_name: value} couvrant exactement FEATURE_COLS.
    """
    dep_time = pd.to_datetime(flight["departure_airport_time"])
    hour = dep_time.hour
    dow = dep_time.dayofweek

    # Météo : valeur réelle ou défaut neutre
    w = weather or {}
    def wval(key):
        v = w.get(key)
        return v if v is not None else WEATHER_DEFAULTS[key]

    weather_code = int(wval("weather_code"))

    layover = flight.get("layover_duration") or 0

    feats = {
        "duration":               float(flight.get("duration") or 0),
        "layover_duration":       float(layover),
        "total_journey_duration": float(flight.get("total_journey_duration") or 0),
        "price":                  float(flight.get("price") or 0),
        "hour_of_day":            float(hour),
        "day_of_week":            float(dow),
        "pos":                    float(flight.get("pos") or 0),
        "is_best":                float(1 if flight.get("is_best") else 0),
        "is_overnight":           float(1 if (hour >= 21 or hour <= 5) else 0),
        "has_layover":            float(1 if layover > 0 else 0),
        "airline_code":           float(encode_category(flight.get("airline"), mappings["airline"])),
        "dep_airport_code":       float(encode_category(flight.get("departure_airport_code"), mappings["departure_airport_code"])),
        "arr_airport_code":       float(encode_category(flight.get("arrival_airport_code"), mappings["arrival_airport_code"])),
        "temperature_c":          float(wval("temperature_c")),
        "precipitation_mm":       float(wval("precipitation_mm")),
        "weather_code":           float(weather_code),
        "wind_speed_kmh":         float(wval("wind_speed_kmh")),
        "visibility_m":           float(wval("visibility_m")),
        "snowfall_cm":            float(wval("snowfall_cm")),
        "weather_risk_score":     float(WMO_RISK.get(weather_code, 0)),
    }
    return feats


def features_to_vector(feats: dict) -> list:
    """Convertit le dict de features en liste ordonnée selon FEATURE_COLS."""
    return [feats[col] for col in FEATURE_COLS]
