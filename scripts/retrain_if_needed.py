from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

import mlflow
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from sklearn.metrics import average_precision_score, roc_auc_score

from src.modeling.train import train_model


def eval_model_on_val(model, X_val: pd.DataFrame, y_val: pd.Series) -> dict[str, float]:
    # model is sklearn pipeline
    proba = model.predict_proba(X_val)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(y_val, proba)) if len(np.unique(y_val)) >= 2 else float("nan"),
        "pr_auc": float(average_precision_score(y_val, proba)) if len(np.unique(y_val)) >= 2 else float("nan"),
    }


def load_champion(model_name: str, alias: str = "champion") -> Optional[str]:
    client = MlflowClient()
    try:
        rm = client.get_registered_model(model_name)
        v = rm.aliases.get(alias)
        if v is None:
            return None
        return f"models:/{model_name}/{v}"
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--processed", default="data/processed", help="Dir with train/val parquet")
    ap.add_argument("--model-name", default="xgb_churn")
    ap.add_argument("--alias", default="champion")
    ap.add_argument("--drift-report", default="reports/drift_live.json")
    ap.add_argument("--perf-report", default="reports/monitoring_snapshot.json")
    ap.add_argument("--drift-threshold", type=float, default=0.25)
    ap.add_argument("--min-roc-auc", type=float, default=0.72, help="If live ROC-AUC drops below this, retrain.")
    ap.add_argument("--promote-delta", type=float, default=0.002, help="New model must beat champion by this ROC-AUC.")
    args = ap.parse_args()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    drift = json.loads(Path(args.drift_report).read_text(encoding="utf-8")) if Path(args.drift_report).exists() else {}
    perf = json.loads(Path(args.perf_report).read_text(encoding="utf-8")) if Path(args.perf_report).exists() else {}

    worst_psi = (drift.get("worst_psi") or drift.get("drift", {}).get("worst_psi"))  # support both
    if worst_psi is None:
        worst_psi = drift.get("psi_numeric", {}) and max(drift["psi_numeric"].values())
    try:
        worst_psi = float(worst_psi) if worst_psi is not None else 0.0
    except Exception:
        worst_psi = 0.0

    live_roc = perf.get("performance", {}).get("roc_auc")
    try:
        live_roc = float(live_roc) if live_roc is not None else float("nan")
    except Exception:
        live_roc = float("nan")

    should_retrain = (worst_psi >= args.drift_threshold) or (not np.isnan(live_roc) and live_roc < args.min_roc_auc)
    if not should_retrain:
        print("No retraining triggered.")
        print(f"worst_psi={worst_psi:.3f}, live_roc_auc={live_roc}")
        return

    print("Retraining triggered.")
    print(f"worst_psi={worst_psi:.3f}, live_roc_auc={live_roc}")

    train_df = pd.read_parquet(Path(args.processed) / "train.parquet")
    val_df = pd.read_parquet(Path(args.processed) / "val.parquet")
    X_val = val_df.drop(columns=["churn"])
    y_val = val_df["churn"].astype(int)

    # Train a new model using same params from params.yaml (reuse train_model defaults via scripts/train_local for simplicity)
    import yaml
    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    model_params = params["model"]
    threshold = float(params["eval"]["threshold"])

    model, _ = train_model(train_df, model_params=model_params, threshold=threshold)

    new_metrics = eval_model_on_val(model, X_val, y_val)
    print("New model val metrics:", new_metrics)

    # Evaluate current champion if exists
    champ_uri = load_champion(args.model_name, alias=args.alias)
    champ_metrics = None
    if champ_uri:
        champ = mlflow.sklearn.load_model(champ_uri)
        champ_metrics = eval_model_on_val(champ, X_val, y_val)
        print("Champion val metrics:", champ_metrics)

    # Log and register new model
    mlflow.set_experiment("enterprise_mlops_retrain")
    with mlflow.start_run():
        mlflow.log_params(model_params)
        mlflow.log_metrics({f"val_{k}": v for k, v in new_metrics.items()})
        res = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=args.model_name,
        )

    client = MlflowClient()
    versions = client.search_model_versions(f"name='{args.model_name}'")
    latest = max(versions, key=lambda v: int(v.version))
    new_version = int(latest.version)

    # Decide promotion
    promote = False
    if champ_metrics is None:
        promote = True
    else:
        if (new_metrics["roc_auc"] - champ_metrics["roc_auc"]) >= args.promote_delta:
            promote = True

    if promote:
        client.set_registered_model_alias(args.model_name, args.alias, str(new_version))
        print(f"PROMOTED: {args.model_name} version {new_version} -> alias {args.alias}")
    else:
        client.set_registered_model_alias(args.model_name, "challenger", str(new_version))
        print(f"NOT PROMOTED: set alias challenger to version {new_version}")
