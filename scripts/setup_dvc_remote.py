from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def run(cmd: list[str]) -> None:
    print(" ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    name = cfg["remote_name"]
    url = cfg["url"]
    make_default = bool(cfg.get("default", True))

    run(["dvc", "remote", "add", "-f", name, url])
    if make_default:
        run(["dvc", "remote", "default", name])

    if "endpointurl" in cfg:
        run(["dvc", "remote", "modify", name, "endpointurl", str(cfg["endpointurl"])])

    print("DVC remote configured. Use env vars/AWS profile for creds (no secrets committed).")


if __name__ == "__main__":
    main()
