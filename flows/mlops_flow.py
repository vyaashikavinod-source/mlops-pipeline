from __future__ import annotations

import subprocess
from prefect import flow, task


@task(retries=2, retry_delay_seconds=5)
def run_cmd(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


@flow(name="enterprise-mlops-pipeline")
def mlops_pipeline() -> None:
    run_cmd(["dvc", "repro"])


if __name__ == "__main__":
    mlops_pipeline()
