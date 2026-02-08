from __future__ import annotations

import argparse
from typing import Any

from src.monitoring.alerting import send_email_from_env, send_slack
from src.utils.io import read_json, write_json
import os


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift", required=True, help="Drift report JSON")
    ap.add_argument("--threshold", type=float, default=0.25)
    ap.add_argument("--out", default="reports/drift_alert.json")
    ap.add_argument("--email", action="store_true", help="Send email alert if SMTP env vars are configured")
    ap.add_argument("--slack", action="store_true", help="Send Slack alert if SLACK_WEBHOOK_URL is configured")
    args = ap.parse_args()

    drift: dict[str, Any] = read_json(args.drift)
    psi_map = drift.get("psi_numeric", {}) or {}

    worst_feature = None
    worst_val = -1.0
    for k, v in psi_map.items():
        try:
            fv = float(v)
        except Exception:
            continue
        if fv > worst_val:
            worst_val = fv
            worst_feature = k

    alert = {
        "threshold": args.threshold,
        "worst_feature": worst_feature,
        "worst_psi": worst_val,
        "alert": bool(worst_val >= args.threshold),
    }
    write_json(args.out, alert)

    if not alert["alert"]:
        print(f"No drift alert. Worst PSI={worst_val:.3f} (threshold {args.threshold}).")
        return

    msg = f"Drift alert: PSI={worst_val:.3f} on feature '{worst_feature}' (threshold {args.threshold})"
    print("ALERT:", msg)

    # Slack (optional)
    if args.slack:
        webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        if webhook:
            send_slack(webhook, f"🚨 {msg}")

    # Email (optional)
    if args.email:
        sent = send_email_from_env(subject="MLOps Drift Alert", body=msg)
        if not sent:
            print("Email not sent: missing SMTP_HOST / ALERT_EMAIL_TO / ALERT_EMAIL_FROM")


if __name__ == "__main__":
    main()
