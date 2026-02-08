from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import mlflow
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.features.preprocess import build_preprocessor, split_xy
from src.modeling.schema import CHURN_SPEC
from src.utils.io import ensure_dir, write_json


@dataclass(frozen=True)
class TrainOutputs:
    metrics: dict[str, float]
    model_path: Path
    meta_path: Path


def train_model(
    df: pd.DataFrame,
    model_params: dict[str, Any],
    threshold: float = 0.5,
    seed: int = 42,
) -> tuple[Pipeline, TrainOutputs]:
    X, y = split_xy(df, CHURN_SPEC)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    pre = build_preprocessor(CHURN_SPEC)
    clf = XGBClassifier(
        **model_params,
        objective="binary:logistic",
        eval_metric="logloss",
        n_jobs=-1,
        random_state=seed,
    )

    pipe = Pipeline([("preprocess", pre), ("model", clf)])
    pipe.fit(X_train, y_train)

    proba = pipe.predict_proba(X_val)[:, 1]
    pred = (proba >= threshold).astype(int)

    metrics = {
        "roc_auc": float(roc_auc_score(y_val, proba)),
        "pr_auc": float(average_precision_score(y_val, proba)),
        "f1": float(f1_score(y_val, pred)),
        "precision": float(precision_score(y_val, pred, zero_division=0)),
        "recall": float(recall_score(y_val, pred, zero_division=0)),
        "val_positive_rate": float(np.mean(y_val)),
        "pred_positive_rate": float(np.mean(pred)),
    }

    ensure_dir("reports")
    write_json("reports/metrics.json", metrics)

    ensure_dir("models")
    model_path = Path("models/model.joblib")
    joblib.dump(pipe, model_path)

    meta = {
        "features_numeric": list(CHURN_SPEC.numeric),
        "features_categorical": list(CHURN_SPEC.categorical),
        "target": CHURN_SPEC.target,
    }
    meta_path = Path("models/model_meta.json")
    write_json(meta_path, meta)

    return pipe, TrainOutputs(metrics=metrics, model_path=model_path, meta_path=meta_path)


def log_and_register(
    pipe: Pipeline,
    X_example: pd.DataFrame,
    model_name: str,
    alias: Optional[str] = None,
) -> int:
    signature = infer_signature(X_example, pipe.predict_proba(X_example)[:, 1])

    with mlflow.start_run():
        res = mlflow.sklearn.log_model(
            sk_model=pipe,
            artifact_path="model",
            registered_model_name=model_name,
            signature=signature,
            input_example=X_example.head(5),
        )

        from mlflow import MlflowClient
        client = MlflowClient()
        versions = client.search_model_versions(f"name='{model_name}'")
        latest = max(versions, key=lambda v: int(v.version))
        version = int(latest.version)

        if alias:
            client.set_registered_model_alias(name=model_name, alias=alias, version=str(version))

        return version
