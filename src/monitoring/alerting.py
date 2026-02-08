from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional

import requests


def _split_recipients(s: str) -> list[str]:
    # supports comma/semicolon separated
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]


def send_slack(webhook: str, text: str) -> None:
    try:
        requests.post(webhook, json={"text": text}, timeout=10).raise_for_status()
    except Exception:
        # do not crash monitoring runs because Slack failed
        return


def send_email_smtp(
    subject: str,
    body: str,
    to_addrs: Iterable[str],
    from_addr: str,
    host: str,
    port: int,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_starttls: bool = True,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(list(to_addrs))
    msg.set_content(body)

    with smtplib.SMTP(host=host, port=port, timeout=20) as server:
        server.ehlo()
        if use_starttls:
            server.starttls()
            server.ehlo()
        if username and password:
            server.login(username, password)
        server.send_message(msg)


def send_email_from_env(subject: str, body: str) -> bool:
    """Send email using SMTP config from environment variables.
    Returns True if attempted with required config present, False otherwise.
    """
    host = os.getenv("SMTP_HOST", "")
    to_s = os.getenv("ALERT_EMAIL_TO", "")
    from_addr = os.getenv("ALERT_EMAIL_FROM", "")
    if not host or not to_s or not from_addr:
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "") or None
    password = os.getenv("SMTP_PASSWORD", "") or None
    use_starttls = os.getenv("SMTP_STARTTLS", "true").lower() in ("1", "true", "yes", "y")

    to_addrs = _split_recipients(to_s)
    send_email_smtp(
        subject=subject,
        body=body,
        to_addrs=to_addrs,
        from_addr=from_addr,
        host=host,
        port=port,
        username=username,
        password=password,
        use_starttls=use_starttls,
    )
    return True
