from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from src.utils.io import write_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLAlchemy DB URL (monitoring db)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    engine = create_engine(args.db, pool_pre_ping=True)

    q = text(
        "SELECT churn_probability, actual_churn FROM predictions WHERE has_feedback = true AND actual_churn IS NOT NULL"
    )
    with engine.connect() as conn:
        rows = conn.execute(q).fetchall()

    if not rows:
        write_json(args.out, {"note": "no feedback rows yet"})
        print("No feedback rows yet.")
        return

    probs = np.array([float(r[0]) for r in rows])
    y = np.array([int(r[1]) for r in rows])

    # Guard against single-class feedback
    metrics = {"n_feedback": int(len(rows))}
    if len(np.unique(y)) >= 2:
        metrics["roc_auc"] = float(roc_auc_score(y, probs))
        metrics["pr_auc"] = float(average_precision_score(y, probs))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["note"] = "feedback currently single-class; AUC undefined"

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
