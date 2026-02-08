from __future__ import annotations

import argparse
from pathlib import Path

import yaml
import pandas as pd

from src.modeling.train import train_model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    model_params = params["model"]
    threshold = float(params["eval"]["threshold"])

    df = pd.read_parquet(Path(args.data) / "train.parquet")
    train_model(df, model_params=model_params, threshold=threshold)
    print("Saved model artifacts to models/ and reports/.")


if __name__ == "__main__":
    main()
