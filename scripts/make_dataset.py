from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    params = yaml.safe_load(Path("params.yaml").read_text(encoding="utf-8"))
    n = int(params["data"]["n_rows"])
    seed = int(params["data"]["random_seed"])
    rng = np.random.default_rng(seed)

    contract = rng.choice(["month-to-month", "one-year", "two-year"], size=n, p=[0.55, 0.25, 0.20])
    payment = rng.choice(["credit_card", "bank_transfer", "paypal", "cash"], size=n, p=[0.35, 0.30, 0.25, 0.10])
    internet = rng.choice(["fiber", "dsl", "none"], size=n, p=[0.55, 0.35, 0.10])
    region = rng.choice(["NE", "SE", "MW", "SW", "W"], size=n)

    tenure = rng.integers(0, 72, size=n).astype(float)
    monthly = rng.normal(75, 25, size=n).clip(10, 200)
    tickets = rng.poisson(1.2, size=n).clip(0, 15).astype(float)
    total = (monthly * tenure + rng.normal(0, 100, size=n)).clip(0)

    logit = (
        -0.02 * tenure
        + 0.10 * tickets
        + 0.008 * (monthly - 70)
        + 0.6 * (contract == "month-to-month").astype(float)
        + 0.25 * (internet == "fiber").astype(float)
        + 0.5 * (payment == "cash").astype(float)
    )
    p = sigmoid(logit)
    churn = rng.binomial(1, p, size=n)

    df = pd.DataFrame(
        {
            "tenure_months": tenure,
            "monthly_charges": monthly,
            "total_charges": total,
            "tickets_90d": tickets,
            "contract_type": contract,
            "payment_method": payment,
            "internet_service": internet,
            "region": region,
            "churn": churn,
        }
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} rows to {out}")


if __name__ == "__main__":
    main()
