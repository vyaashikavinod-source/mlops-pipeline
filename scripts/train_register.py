from __future__ import annotations

import argparse
from pathlib import Path

import mlflow
import pandas as pd
import yaml

from src.modeling.train import log_and_register, train_model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Processed data dir containing train.parquet")
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--alias", default="champion")
    args = ap.parse_args()

    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    model_params = params["model"]
    threshold = float(params["eval"]["threshold"])

    df = pd.read_parquet(Path(args.data) / "train.parquet")
    pipe, _ = train_model(df, model_params=model_params, threshold=threshold)

    X_example = df.drop(columns=["churn"]).head(200)

    mlflow.set_experiment("enterprise_mlops_churn")
    version = log_and_register(pipe, X_example=X_example, model_name=args.model_name, alias=args.alias)

    print(f"Registered model '{args.model_name}' version={version} alias={args.alias}")


if __name__ == "__main__":
    main()
