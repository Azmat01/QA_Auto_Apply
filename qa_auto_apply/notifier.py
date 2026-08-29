"""Optional SMTP notification for the daily digest."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

logger = logging.getLogger("qa_auto_apply.notifier")


def send_digest_email(
    digest_path: Path,
    *,
    to_address: str,
    subject: str,
    job_count: int,
) -> bool:
    """Send digest.md over SMTP when SMTP_USERNAME and SMTP_PASSWORD are set.

    Returns True when a message was sent. Missing credentials skip send (not an error).
    """
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    if not username or not password:
        logger.info("SMTP credentials not set; skipping email send")
        return False

    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    from_address = os.getenv("SMTP_FROM", username).strip()
    body = digest_path.read_text(encoding="utf-8") if digest_path.is_file() else ""

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message["X-QA-Auto-Apply-Label"] = "QA-auto-apply"
    message.set_content(
        f"{job_count} matching QA / SDET roles (India or Remote).\n\n{body}"
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(username, password)
            smtp.send_message(message)
        logger.info("Digest email sent", extra={"company": to_address})
        return True
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to send digest email")
        raise
