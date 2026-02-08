from __future__ import annotations

import os
import subprocess
from prefect import flow, task


@task(retries=2, retry_delay_seconds=10)
def run_cmd(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


@flow(name="model-monitoring-daily")
def monitoring_daily() -> None:
    db = os.getenv("MONITORING_DB_URL", "")
    if not db:
        raise RuntimeError("MONITORING_DB_URL not set")

    baseline = "data/processed/train.parquet"

    # 1) Materialize daily KPIs + segment metrics into monitoring DB (Grafana reads these tables)
    run_cmd(["python", "scripts/materialize_metrics.py", "--db", db, "--baseline", baseline, "--out", "reports/monitoring_snapshot.json"])

    # 2) Drift alert (Slack + Email are optional; require env vars)
    run_cmd(["python", "scripts/drift_alert.py", "--drift", "reports/monitoring_snapshot.json", "--threshold", "0.25", "--email", "--slack"])

    # 3) Retrain & promote if needed
    run_cmd(["python", "scripts/retrain_if_needed.py", "--processed", "data/processed", "--model-name", "xgb_churn", "--alias", "champion", "--drift-report", "reports/monitoring_snapshot.json", "--perf-report", "reports/monitoring_snapshot.json"])


if __name__ == "__main__":
    monitoring_daily()
