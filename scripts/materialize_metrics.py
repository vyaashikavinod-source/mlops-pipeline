from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.modeling.schema import CHURN_SPEC
from src.monitoring.db import insert_daily_metrics, insert_segment_metrics
from src.utils.io import write_json


def expected_calibration_error(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p >= lo) & (p < hi) if i < n_bins - 1 else (p >= lo) & (p <= hi)
        if mask.sum() == 0:
            continue
        acc = y[mask].mean()
        conf = p[mask].mean()
        ece += (mask.sum() / len(y)) * abs(acc - conf)
    return float(ece)


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


def safe_auc(y: np.ndarray, p: np.ndarray) -> tuple[Optional[float], Optional[float]]:
    if len(np.unique(y)) < 2:
        return None, None
    return float(roc_auc_score(y, p)), float(average_precision_score(y, p))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLAlchemy DB URL")
    ap.add_argument("--baseline", required=True, help="Baseline train parquet for drift")
    ap.add_argument("--recent-n", type=int, default=10000, help="Use last N predictions for drift")
    ap.add_argument("--out", default="reports/monitoring_snapshot.json")
    ap.add_argument("--min-seg-n", type=int, default=200, help="Minimum examples in segment to compute metrics")
    args = ap.parse_args()

    engine = create_engine(args.db, pool_pre_ping=True)

    # Counts
    with engine.connect() as conn:
        n_predictions = int(conn.execute(text("SELECT COUNT(*) FROM predictions")).scalar() or 0)
        n_feedback = int(conn.execute(text("SELECT COUNT(*) FROM predictions WHERE has_feedback = true")).scalar() or 0)

    # Performance metrics (only on feedback rows)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT churn_probability, actual_churn FROM predictions WHERE has_feedback = true AND actual_churn IS NOT NULL")
        ).fetchall()

    roc_auc = pr_auc = brier = ece = None
    if rows:
        probs = np.array([float(r[0]) for r in rows])
        y = np.array([int(r[1]) for r in rows])
        roc_auc, pr_auc = safe_auc(y, probs)
        brier = float(brier_score_loss(y, probs))
        ece = expected_calibration_error(y, probs, n_bins=10)

    # Drift on recent N predictions
    baseline = pd.read_parquet(args.baseline)
    with engine.connect() as conn:
        r2 = conn.execute(
            text("SELECT request_json FROM predictions ORDER BY id DESC LIMIT :n"),
            {"n": args.recent_n},
        ).fetchall()

    worst_feature = None
    worst_psi = None
    psi_numeric: dict[str, float] = {}
    if r2:
        reqs = [json.loads(r[0]) for r in r2]
        current = pd.DataFrame(reqs)

        for col in CHURN_SPEC.numeric:
            psi_numeric[col] = psi(baseline[col].to_numpy(), current[col].to_numpy(), bins=10)

        worst_feature, worst_psi = max(psi_numeric.items(), key=lambda kv: kv[1])

    # Materialize daily metrics into DB (for Grafana)
    insert_daily_metrics(
        args.db,
        n_predictions=n_predictions,
        n_feedback=n_feedback,
        roc_auc=roc_auc,
        pr_auc=pr_auc,
        brier=brier,
        ece=ece,
        worst_feature=worst_feature,
        worst_psi=worst_psi,
    )

    # Segment metrics (cohort slicing) using feedback rows only
    segment_rows_out = {}
    if rows:
        # Fetch request_json + label for feedback rows
        with engine.connect() as conn:
            fb = conn.execute(
                text("SELECT request_json, churn_probability, actual_churn FROM predictions WHERE has_feedback = true AND actual_churn IS NOT NULL")
            ).fetchall()
        reqs = [json.loads(r[0]) for r in fb]
        probs = np.array([float(r[1]) for r in fb])
        y = np.array([int(r[2]) for r in fb])
        df = pd.DataFrame(reqs)
        df["__p"] = probs
        df["__y"] = y

        for seg in list(CHURN_SPEC.categorical):
            agg_rows = []
            for val, g in df.groupby(seg):
                if len(g) < args.min_seg_n:
                    continue
                ra, pa = safe_auc(g["__y"].to_numpy(), g["__p"].to_numpy())
                br = float(brier_score_loss(g["__y"].to_numpy(), g["__p"].to_numpy()))
                agg_rows.append((str(val), int(len(g)), ra, pa, br))
            if agg_rows:
                insert_segment_metrics(args.db, seg, agg_rows)
                segment_rows_out[seg] = [
                    {"value": v, "n": n, "roc_auc": ra, "pr_auc": pa, "brier": br} for (v, n, ra, pa, br) in agg_rows
                ]

    snapshot: dict[str, Any] = {
        "n_predictions": n_predictions,
        "n_feedback": n_feedback,
        "performance": {"roc_auc": roc_auc, "pr_auc": pr_auc, "brier": brier, "ece": ece},
        "drift": {"psi_numeric": psi_numeric, "worst_feature": worst_feature, "worst_psi": worst_psi},
        "segments": segment_rows_out,
        "notes": "AUC metrics require feedback labels. Drift uses recent logged predictions vs baseline train.",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, snapshot)
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
