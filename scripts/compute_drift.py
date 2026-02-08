from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

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
    ap.add_argument("--db", required=True, help="SQLAlchemy DB URL (monitoring db)")
    ap.add_argument("--baseline", required=True, help="Baseline parquet (train)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--recent-n", type=int, default=5000, help="Use last N predictions for drift")
    args = ap.parse_args()

    baseline = pd.read_parquet(args.baseline)

    engine = create_engine(args.db, pool_pre_ping=True)
    q = text("SELECT request_json FROM predictions ORDER BY id DESC LIMIT :n")
    with engine.connect() as conn:
        rows = conn.execute(q, {"n": args.recent_n}).fetchall()

    if not rows:
        write_json(args.out, {"note": "no prediction logs yet"})
        print("No prediction logs yet.")
        return

    import json as pyjson
    reqs = [pyjson.loads(r[0]) for r in rows]
    current = pd.DataFrame(reqs)

    report = {
        "n_recent": int(len(current)),
        "psi_numeric": {},
        "notes": "PSI rule-of-thumb: 0-0.1 none, 0.1-0.25 moderate, >0.25 significant.",
    }

    for col in CHURN_SPEC.numeric:
        report["psi_numeric"][col] = psi(baseline[col].to_numpy(), current[col].to_numpy(), bins=10)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
