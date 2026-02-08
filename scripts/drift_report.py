from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.modeling.schema import CHURN_SPEC
from src.utils.io import write_json


def psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    expected = expected.astype(float)
    actual = actual.astype(float)

    quantiles = np.quantile(expected, np.linspace(0, 1, bins + 1))
    quantiles = np.unique(quantiles)
    if len(quantiles) < 3:
        return 0.0

    e_counts, _ = np.histogram(expected, bins=quantiles)
    a_counts, _ = np.histogram(actual, bins=quantiles)

    e_perc = e_counts / max(e_counts.sum(), 1)
    a_perc = a_counts / max(a_counts.sum(), 1)

    eps = 1e-6
    e_perc = np.clip(e_perc, eps, 1)
    a_perc = np.clip(a_perc, eps, 1)

    return float(np.sum((a_perc - e_perc) * np.log(a_perc / e_perc)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--current", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    baseline = pd.read_parquet(args.baseline)
    current = pd.read_parquet(args.current)

    report = {"psi_numeric": {}, "notes": "PSI: 0-0.1 none, 0.1-0.25 moderate, >0.25 significant."}

    for col in CHURN_SPEC.numeric:
        report["psi_numeric"][col] = psi(baseline[col].to_numpy(), current[col].to_numpy(), bins=10)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, report)
    print(f"Wrote drift report to {out}")


if __name__ == "__main__":
    main()
