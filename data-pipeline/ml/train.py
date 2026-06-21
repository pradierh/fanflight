"""
train.py
--------
Entraîne et compare deux modèles de classification binaire sur le dataset
de retards de vols :

  1. XGBoost         — modèle tabulaire performant, interprétable via SHAP
  2. Réseau de neurones (PyTorch) — démontre l'approche Deep Learning

Tracking complet via MLflow :
  - Paramètres, métriques, artefacts (courbes ROC, matrices de confusion, SHAP)
  - Versioning du modèle dans le MLflow Model Registry
  - Le meilleur modèle est promu en stage "Production"

Usage :
    python train.py
    python train.py --data /chemin/vers/training_set.parquet
"""

import argparse
import logging
import os
from pathlib import Path

import mlflow
import mlflow.pytorch
import mlflow.xgboost
import numpy as np
import pandas as pd
import shap
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset
from xgboost import XGBClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

DATA_PATH   = Path(os.getenv("DATA_DIR", "/opt/spark/data")) / "training_set.parquet"
MLFLOW_URI  = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
ARTIFACT_DIR = Path("/tmp/mlflow_artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "duration", "layover_duration", "total_journey_duration", "price",
    "hour_of_day", "day_of_week", "pos",
    "is_best", "is_overnight", "has_layover",
    "airline_code", "dep_airport_code", "arr_airport_code",
    "temperature_c", "precipitation_mm", "weather_code",
    "wind_speed_kmh", "visibility_m", "snowfall_cm", "weather_risk_score",
]
LABEL_COL = "is_delayed"

RANDOM_STATE = 42
TEST_SIZE    = 0.2


# ------------------------------------------------------------------
# Chargement des données
# ------------------------------------------------------------------

def load_data(path: Path):
    df = pd.read_parquet(path)
    log.info(f"Dataset chargé : {len(df)} lignes")

    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df[LABEL_COL].values.astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc  = scaler.transform(X_test)

    return X_train, X_test, X_train_sc, X_test_sc, y_train, y_test, scaler, df[FEATURE_COLS]


# ------------------------------------------------------------------
# Utilitaires de visualisation
# ------------------------------------------------------------------

def plot_confusion_matrix(y_true, y_pred, title: str, path: Path):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_xlabel("Prédit")
    ax.set_ylabel("Réel")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_roc_curve(y_true, y_prob, title: str, path: Path) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    auc = roc_auc_score(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], "k--")
    ax.set_xlabel("Taux faux positifs")
    ax.set_ylabel("Taux vrais positifs")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return auc


def log_metrics(y_true, y_pred, y_prob, prefix: str) -> dict:
    metrics = {
        f"{prefix}_accuracy": accuracy_score(y_true, y_pred),
        f"{prefix}_f1":       f1_score(y_true, y_pred),
        f"{prefix}_auc":      roc_auc_score(y_true, y_prob),
    }
    for k, v in metrics.items():
        mlflow.log_metric(k, v)
    log.info(f"{prefix} — " + " | ".join(f"{k.split('_',1)[1]}={v:.4f}" for k, v in metrics.items()))
    return metrics


# ------------------------------------------------------------------
# 1. XGBoost
# ------------------------------------------------------------------

def train_xgboost(X_train, X_test, y_train, y_test, feature_names):
    params = {
        "n_estimators":     200,
        "max_depth":        5,
        "learning_rate":    0.05,
        "subsample":        0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": (y_train == 0).sum() / (y_train == 1).sum(),  # déséquilibre
        "use_label_encoder": False,
        "eval_metric":      "logloss",
        "random_state":     RANDOM_STATE,
    }

    with mlflow.start_run(run_name="XGBoost", nested=True) as run:
        mlflow.log_params(params)

        model = XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        metrics = log_metrics(y_test, y_pred, y_prob, "test")

        # Courbe ROC
        roc_path = ARTIFACT_DIR / "xgb_roc.png"
        plot_roc_curve(y_test, y_prob, "ROC — XGBoost", roc_path)
        mlflow.log_artifact(str(roc_path))

        # Matrice de confusion
        cm_path = ARTIFACT_DIR / "xgb_confusion.png"
        plot_confusion_matrix(y_test, y_pred, "Confusion — XGBoost", cm_path)
        mlflow.log_artifact(str(cm_path))

        # SHAP — interprétabilité
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)

        shap_fig, ax = plt.subplots(figsize=(8, 6))
        shap.summary_plot(shap_values, X_test, feature_names=feature_names,
                          show=False, plot_type="bar")
        shap_path = ARTIFACT_DIR / "xgb_shap.png"
        plt.tight_layout()
        plt.savefig(shap_path)
        plt.close()
        mlflow.log_artifact(str(shap_path))

        # Log du modèle dans le registry
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            registered_model_name="flight_delay_xgboost",
        )

        log.info(f"XGBoost run_id={run.info.run_id}")
        return metrics["test_auc"], run.info.run_id


# ------------------------------------------------------------------
# 2. Réseau de neurones PyTorch
# ------------------------------------------------------------------

class FlightDelayNet(nn.Module):
    """
    Réseau fully-connected à 3 couches cachées avec BatchNorm et Dropout.
    Architecture adaptée à un dataset tabulaire de taille modeste.
    """

    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),

            nn.Linear(64, 32),
            nn.ReLU(),

            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x).squeeze(1)


def train_neural_network(X_train_sc, X_test_sc, y_train, y_test):
    EPOCHS     = 50
    BATCH_SIZE = 32
    LR         = 1e-3
    PATIENCE   = 10       # early stopping

    params = {
        "architecture": "FC-128-64-32-1",
        "epochs":        EPOCHS,
        "batch_size":    BATCH_SIZE,
        "learning_rate": LR,
        "dropout":       0.3,
        "optimizer":     "Adam",
        "loss":          "BCELoss",
        "patience":      PATIENCE,
    }

    with mlflow.start_run(run_name="NeuralNetwork", nested=True) as run:
        mlflow.log_params(params)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        log.info(f"Device : {device}")

        # Tenseurs
        X_tr = torch.tensor(X_train_sc, dtype=torch.float32).to(device)
        y_tr = torch.tensor(y_train,    dtype=torch.float32).to(device)
        X_te = torch.tensor(X_test_sc,  dtype=torch.float32).to(device)
        y_te = torch.tensor(y_test,     dtype=torch.float32).to(device)

        train_loader = DataLoader(
            TensorDataset(X_tr, y_tr),
            batch_size=BATCH_SIZE,
            shuffle=True,
        )

        model     = FlightDelayNet(input_dim=X_train_sc.shape[1]).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)

        # Pondération de la classe positive pour le déséquilibre
        pos_weight = torch.tensor([(y_train == 0).sum() / (y_train == 1).sum()]).to(device)
        criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

        # Courbes d'apprentissage
        train_losses = []
        val_losses   = []

        best_val_loss   = float("inf")
        patience_counter = 0
        best_state       = None

        for epoch in range(EPOCHS):
            # --- Train ---
            model.train()
            epoch_loss = 0.0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                logits = model.net[:-1](X_batch).squeeze(1)  # avant Sigmoid pour BCEWithLogits
                loss   = criterion(logits, y_batch)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * len(X_batch)

            train_loss = epoch_loss / len(X_tr)

            # --- Validation ---
            model.eval()
            with torch.no_grad():
                logits_val = model.net[:-1](X_te).squeeze(1)
                val_loss   = criterion(logits_val, y_te).item()

            train_losses.append(train_loss)
            val_losses.append(val_loss)

            mlflow.log_metric("train_loss", train_loss, step=epoch)
            mlflow.log_metric("val_loss",   val_loss,   step=epoch)

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss    = val_loss
                patience_counter = 0
                best_state       = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= PATIENCE:
                    log.info(f"Early stopping à l'époque {epoch}")
                    break

        # Restaure le meilleur état
        model.load_state_dict(best_state)

        # --- Évaluation finale ---
        model.eval()
        with torch.no_grad():
            y_prob_tensor = model(X_te)
            y_prob = y_prob_tensor.cpu().numpy()
            y_pred = (y_prob >= 0.5).astype(int)

        metrics = log_metrics(y_test, y_pred, y_prob, "test")

        # Courbe d'apprentissage
        lc_path = ARTIFACT_DIR / "nn_learning_curve.png"
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(train_losses, label="Train loss")
        ax.plot(val_losses,   label="Validation loss")
        ax.set_xlabel("Époque")
        ax.set_ylabel("Loss")
        ax.set_title("Courbe d'apprentissage — Réseau de neurones")
        ax.legend()
        fig.tight_layout()
        fig.savefig(lc_path)
        plt.close(fig)
        mlflow.log_artifact(str(lc_path))

        # Courbe ROC
        roc_path = ARTIFACT_DIR / "nn_roc.png"
        plot_roc_curve(y_test, y_prob, "ROC — Réseau de neurones", roc_path)
        mlflow.log_artifact(str(roc_path))

        # Matrice de confusion
        cm_path = ARTIFACT_DIR / "nn_confusion.png"
        plot_confusion_matrix(y_test, y_pred, "Confusion — Réseau de neurones", cm_path)
        mlflow.log_artifact(str(cm_path))

        # Log du modèle
        mlflow.pytorch.log_model(
            model,
            artifact_path="model",
            registered_model_name="flight_delay_nn",
        )

        log.info(f"NeuralNetwork run_id={run.info.run_id}")
        return metrics["test_auc"], run.info.run_id


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main(data_path: Path):
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment("flight_delay_prediction")

    log.info(f"Chargement des données : {data_path}")
    X_train, X_test, X_train_sc, X_test_sc, y_train, y_test, scaler, features_df = load_data(data_path)

    log.info(f"Train : {len(X_train)} | Test : {len(X_test)}")
    log.info(f"Taux de retard — train : {y_train.mean():.1%} | test : {y_test.mean():.1%}")

    with mlflow.start_run(run_name="FlightDelay_Comparison") as parent_run:
        mlflow.log_param("dataset_rows",    len(X_train) + len(X_test))
        mlflow.log_param("n_features",      len(FEATURE_COLS))
        mlflow.log_param("test_size",       TEST_SIZE)
        mlflow.log_param("delay_rate_train", float(y_train.mean()))

        # Entraînement des deux modèles
        log.info("--- XGBoost ---")
        xgb_auc, xgb_run_id = train_xgboost(
            X_train, X_test, y_train, y_test,
            feature_names=FEATURE_COLS,
        )

        log.info("--- Réseau de neurones ---")
        nn_auc, nn_run_id = train_neural_network(
            X_train_sc, X_test_sc, y_train, y_test,
        )

        # Comparaison finale
        log.info(f"\nRésultats finaux :")
        log.info(f"  XGBoost AUC     : {xgb_auc:.4f}")
        log.info(f"  NeuralNet AUC   : {nn_auc:.4f}")

        mlflow.log_metric("xgb_auc_final", xgb_auc)
        mlflow.log_metric("nn_auc_final",  nn_auc)

        best_model  = "XGBoost" if xgb_auc >= nn_auc else "NeuralNetwork"
        best_run_id = xgb_run_id if xgb_auc >= nn_auc else nn_run_id
        mlflow.log_param("best_model", best_model)

        log.info(f"\nMeilleur modèle : {best_model} (AUC={max(xgb_auc, nn_auc):.4f})")
        log.info(f"Run parent : {parent_run.info.run_id}")

    return best_model, best_run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_PATH)
    args = parser.parse_args()
    main(args.data)
