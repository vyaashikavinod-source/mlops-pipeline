# Email alerts (SMTP)

This repo supports email drift alerts via SMTP.

## Recommended providers
- Gmail (use an **App Password**)
- Outlook/Office365 SMTP
- SendGrid SMTP relay

## Environment variables
Set:
- `SMTP_HOST`
- `SMTP_PORT` (587 recommended)
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_STARTTLS` (true/false)
- `ALERT_EMAIL_FROM`
- `ALERT_EMAIL_TO` (comma-separated recipients)

## Test locally
After you generated a drift report:
```bash
python scripts/drift_alert.py --drift reports/drift_live.json --threshold 0.25 --email
```

If your drift exceeds threshold, you should receive an email.
If not, the script will exit without sending.
