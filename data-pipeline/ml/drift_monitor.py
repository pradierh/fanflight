"""
drift_monitor.py
-----------------
Détecte la dérive des données entre deux batches de vols.

Deux types de mesure :

  1. PSI (Population Stability Index) — mesure la dérive de distribution
     d'une feature entre la référence (données d'entraînement) et un nouveau
     batch. Seuils standard :
       PSI < 0.1  : pas de dérive
       PSI < 0.2  : dérive modérée à surveiller
       PSI >= 0.2 : dérive significative, ré-entraînement recommandé

  2. KS-test (Kolmogorov-Smirnov) — test statistique non-paramétrique.
     La p-value < 0.05 indique une dérive significative.

Usage :
    python drift_monitor.py --reference data/training_set.parquet
                            --current   data/new_batch.parquet

    # Ou depuis Python :
    from drift_monitor import run_drift_report
    report = run_drift_report(df_reference, df_current)
"""

import argparse
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MLFLOW_URI   = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
ARTIFACT_DIR = Path("/tmp/drift_artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# Features à monitorer — on exclut les IDs et les catégorielles encodées
# (la dérive sur airline_code n'est pas interprétable directement)
NUMERIC_FEATURES = [
    "duration", "layover_duration", "total_journey_duration", "price",
    "hour_of_day", "day_of_week",
    "temperature_c", "precipitation_mm", "wind_speed_kmh",
    "visibility_m", "snowfall_cm", "weather_risk_score",
]

CATEGORICAL_FEATURES = [
    "airline", "departure_airport_id", "arrival_airport_id",
]

# Seuils PSI
PSI_WARNING  = 0.1
PSI_CRITICAL = 0.2


# ------------------------------------------------------------------
# PSI
# ------------------------------------------------------------------

def compute_psi(reference: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """
    Calcule le PSI entre deux distributions numériques.
    Les bins sont définis sur la distribution de référence.
    """
    # Evite les erreurs avec des valeurs toutes identiques
    if reference.std() == 0:
        return 0.0

    breakpoints = np.linspace(reference.min(), reference.max(), n_bins + 1)
    breakpoints[0]  -= 1e-9   # inclut la borne inférieure
    breakpoints[-1] += 1e-9   # inclut la borne supérieure

    ref_counts = np.histogram(reference, bins=breakpoints)[0]
    cur_counts = np.histogram(current,   bins=breakpoints)[0]

    # Proportions (évite la division par 0 avec epsilon)
    eps = 1e-6
    ref_pct = ref_counts / (ref_counts.sum() + eps)
    cur_pct = cur_counts / (cur_counts.sum() + eps)

    ref_pct = np.where(ref_pct == 0, eps, ref_pct)
    cur_pct = np.where(cur_pct == 0, eps, cur_pct)

    psi = np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct))
    return float(psi)


def psi_severity(psi: float) -> str:
    if psi < PSI_WARNING:
        return "OK"
    elif psi < PSI_CRITICAL:
        return "WARNING"
    else:
        return "CRITICAL"


# ------------------------------------------------------------------
# KS-test
# ------------------------------------------------------------------

def compute_ks(reference: np.ndarray, current: np.ndarray) -> tuple[float, float]:
    """Retourne (statistique KS, p-value)."""
    stat, pvalue = stats.ks_2samp(reference, current)
    return float(stat), float(pvalue)


# ------------------------------------------------------------------
# Dérive catégorielle (Chi-2 sur les fréquences)
# ------------------------------------------------------------------

def compute_categorical_drift(reference: pd.Series, current: pd.Series) -> dict:
    """
    Compare la distribution des catégories entre référence et current.
    Utilise un test du Chi-2 sur les fréquences relatives.
    """
    ref_freq = reference.value_counts(normalize=True)
    cur_freq = current.value_counts(normalize=True)

    all_cats = ref_freq.index.union(cur_freq.index)
    ref_aligned = ref_freq.reindex(all_cats, fill_value=0)
    cur_aligned = cur_freq.reindex(all_cats, fill_value=0)

    # Chi-2 (scipy attend des fréquences absolues)
    ref_abs = (ref_aligned * len(reference)).values
    cur_abs = (cur_aligned * len(current)).values

    # Evite les bins vides
    mask = (ref_abs + cur_abs) > 0
    if mask.sum() < 2:
        return {"chi2": 0.0, "pvalue": 1.0, "drift": False}

    chi2, pvalue = stats.chisquare(cur_abs[mask], f_exp=ref_abs[mask])
    return {
        "chi2":  float(chi2),
        "pvalue": float(pvalue),
        "drift": bool(pvalue < 0.05),
    }


# ------------------------------------------------------------------
# Visualisation
# ------------------------------------------------------------------

def plot_distribution_comparison(ref: np.ndarray, cur: np.ndarray,
                                  feature_name: str, psi: float, path: Path):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(ref, bins=20, alpha=0.5, label="Référence (train)", density=True, color="steelblue")
    ax.hist(cur, bins=20, alpha=0.5, label="Batch courant",     density=True, color="orangered")
    severity = psi_severity(psi)
    color_map = {"OK": "green", "WARNING": "orange", "CRITICAL": "red"}
    ax.set_title(f"{feature_name} — PSI={psi:.4f} [{severity}]",
                 color=color_map[severity])
    ax.set_xlabel(feature_name)
    ax.set_ylabel("Densité")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_drift_summary(report: dict, path: Path):
    """Heatmap de synthèse des PSI par feature."""
    features  = [r["feature"] for r in report["numeric"]]
    psi_vals  = [r["psi"]     for r in report["numeric"]]
    severities = [r["severity"] for r in report["numeric"]]

    colors = {"OK": "#2ecc71", "WARNING": "#f39c12", "CRITICAL": "#e74c3c"}
    bar_colors = [colors[s] for s in severities]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(features, psi_vals, color=bar_colors)
    ax.axvline(PSI_WARNING,  color="orange", linestyle="--", label=f"Warning  ({PSI_WARNING})")
    ax.axvline(PSI_CRITICAL, color="red",    linestyle="--", label=f"Critical ({PSI_CRITICAL})")
    ax.set_xlabel("PSI")
    ax.set_title(f"Drift Monitor — {report['batch_date']}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


# ------------------------------------------------------------------
# Rapport complet
# ------------------------------------------------------------------

def run_drift_report(df_ref: pd.DataFrame, df_cur: pd.DataFrame,
                     log_to_mlflow: bool = True) -> dict:

    report = {
        "batch_date":  datetime.utcnow().isoformat(),
        "ref_rows":    len(df_ref),
        "cur_rows":    len(df_cur),
        "numeric":     [],
        "categorical": [],
        "summary":     {},
    }

    # --- Features numériques ---
    critical_features = []

    for feat in NUMERIC_FEATURES:
        if feat not in df_ref.columns or feat not in df_cur.columns:
            continue

        ref_vals = df_ref[feat].dropna().values
        cur_vals = df_cur[feat].dropna().values

        if len(ref_vals) < 5 or len(cur_vals) < 5:
            continue

        psi             = compute_psi(ref_vals, cur_vals)
        ks_stat, pvalue = compute_ks(ref_vals, cur_vals)
        severity        = psi_severity(psi)

        entry = {
            "feature":  feat,
            "psi":      round(psi, 5),
            "severity": severity,
            "ks_stat":  round(ks_stat, 5),
            "ks_pvalue": round(pvalue, 5),
            "ks_drift": bool(pvalue < 0.05),
        }
        report["numeric"].append(entry)

        if severity == "CRITICAL":
            critical_features.append(feat)

        # Plot par feature
        plot_path = ARTIFACT_DIR / f"drift_{feat}.png"
        plot_distribution_comparison(ref_vals, cur_vals, feat, psi, plot_path)

    # --- Features catégorielles ---
    for feat in CATEGORICAL_FEATURES:
        if feat not in df_ref.columns or feat not in df_cur.columns:
            continue
        cat_result = compute_categorical_drift(df_ref[feat], df_cur[feat])
        cat_result["feature"] = feat
        report["categorical"].append(cat_result)

    # --- Dérive du label (distribution des retards) ---
    if "is_delayed" in df_ref.columns and "is_delayed" in df_cur.columns:
        ref_delay_rate = float(df_ref["is_delayed"].mean())
        cur_delay_rate = float(df_cur["is_delayed"].mean())
        delta = abs(cur_delay_rate - ref_delay_rate)
        report["label_drift"] = {
            "ref_delay_rate": round(ref_delay_rate, 4),
            "cur_delay_rate": round(cur_delay_rate, 4),
            "delta":          round(delta, 4),
            "alert":          bool(delta > 0.05),  # alerte si +5 points
        }

    # --- Synthèse ---
    n_critical = sum(1 for r in report["numeric"] if r["severity"] == "CRITICAL")
    n_warning  = sum(1 for r in report["numeric"] if r["severity"] == "WARNING")
    report["summary"] = {
        "critical_features": critical_features,
        "n_critical":        n_critical,
        "n_warning":         n_warning,
        "retrain_recommended": n_critical >= 1,
    }

    # Plot de synthèse
    summary_path = ARTIFACT_DIR / "drift_summary.png"
    plot_drift_summary(report, summary_path)

    # --- MLflow ---
    if log_to_mlflow:
        mlflow.set_tracking_uri(MLFLOW_URI)
        mlflow.set_experiment("flight_delay_drift_monitoring")

        with mlflow.start_run(run_name=f"drift_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"):
            mlflow.log_param("ref_rows", report["ref_rows"])
            mlflow.log_param("cur_rows", report["cur_rows"])

            for entry in report["numeric"]:
                mlflow.log_metric(f"psi_{entry['feature']}",    entry["psi"])
                mlflow.log_metric(f"ks_pvalue_{entry['feature']}", entry["ks_pvalue"])

            mlflow.log_metric("n_critical_features", n_critical)
            mlflow.log_metric("n_warning_features",  n_warning)

            if "label_drift" in report:
                mlflow.log_metric("label_drift_delta", report["label_drift"]["delta"])

            # Artefacts
            mlflow.log_artifact(str(summary_path))
            for feat in NUMERIC_FEATURES:
                p = ARTIFACT_DIR / f"drift_{feat}.png"
                if p.exists():
                    mlflow.log_artifact(str(p))

            # Rapport JSON complet
            report_path = ARTIFACT_DIR / "drift_report.json"
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)
            mlflow.log_artifact(str(report_path))

    # Log console
    log.info(f"\n--- Rapport de dérive ---")
    log.info(f"Référence : {report['ref_rows']} lignes | Batch : {report['cur_rows']} lignes")
    log.info(f"Features critiques  : {n_critical}")
    log.info(f"Features en warning : {n_warning}")
    if critical_features:
        log.warning(f"DRIFT CRITIQUE sur : {critical_features}")
    if report["summary"]["retrain_recommended"]:
        log.warning("RE-ENTRAINEMENT RECOMMANDE")
    else:
        log.info("Pas de dérive critique détectée.")

    return report


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path,
                        default=Path(os.getenv("DATA_DIR", "/opt/spark/data")) / "training_set.parquet")
    parser.add_argument("--current",   type=Path, required=False,
                        help="Nouveau batch à comparer. Si absent, simule une dérive.")
    args = parser.parse_args()

    df_ref = pd.read_parquet(args.reference)

    if args.current and args.current.exists():
        df_cur = pd.read_parquet(args.current)
    else:
        # Simulation de dérive pour démonstration (utile sans nouveau batch réel)
        log.info("Pas de batch courant fourni — simulation d'une dérive artificielle.")
        df_cur = df_ref.copy()
        rng = np.random.default_rng(42)
        # Dérive sur price : +20%
        df_cur["price"]          = df_cur["price"]          * rng.uniform(1.1, 1.3, len(df_cur))
        # Dérive sur precipitation : événements extrêmes simulés
        df_cur["precipitation_mm"] = df_cur["precipitation_mm"] + rng.exponential(5, len(df_cur))
        # Dérive sur wind_speed
        df_cur["wind_speed_kmh"] = df_cur["wind_speed_kmh"] * rng.uniform(1.2, 1.8, len(df_cur))

    report = run_drift_report(df_ref, df_cur, log_to_mlflow=True)
    return report


if __name__ == "__main__":
    main()
