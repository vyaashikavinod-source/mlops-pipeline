from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.inp)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for col in ["contract_type", "payment_method", "internet_service", "region"]:
        df[col] = df[col].astype(str).fillna("unknown")

    train = df.sample(frac=0.8, random_state=42)
    val = df.drop(train.index)

    train.to_parquet(out_dir / "train.parquet", index=False)
    val.to_parquet(out_dir / "val.parquet", index=False)
    print(f"Wrote train/val parquet to {out_dir}")


if __name__ == "__main__":
    main()
