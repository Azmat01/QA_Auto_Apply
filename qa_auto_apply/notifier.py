"""Optional SMTP notification for the daily digest."""

from __future__ import annotations

import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from qa_auto_apply.models import JobListing

logger = logging.getLogger("qa_auto_apply.notifier")


def send_digest_email(
    digest_path: Path,
    *,
    to_address: str,
    subject: str,
    jobs: list[JobListing] | None = None,
    job_count: int | None = None,
) -> bool:
    """Send a clickable job list over SMTP when SMTP_USERNAME and SMTP_PASSWORD are set.

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
    listings = list(jobs or [])
    count = job_count if job_count is not None else len(listings)
    digest = digest_path.read_text(encoding="utf-8") if digest_path.is_file() else ""
    plain, html_body = _email_bodies(listings, count=count, digest=digest)

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_address
    message["To"] = to_address
    message["X-QA-Auto-Apply-Label"] = "QA-auto-apply"
    message.set_content(plain)
    message.add_alternative(html_body, subtype="html")

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


def _email_bodies(
    jobs: list[JobListing],
    *,
    count: int,
    digest: str,
) -> tuple[str, str]:
    if not jobs:
        plain = (
            f"{count} junior QA / Manual Tester roles (India or Remote).\n\n"
            "No matching openings were found in this run.\n"
        )
        if digest:
            plain += f"\n{digest}\n"
        html_body = (
            "<p>No matching junior QA Engineer / Manual Tester openings "
            "were found for India or Remote.</p>"
        )
        return plain, html_body

    plain_lines = [
        f"{count} junior QA / Manual Tester roles (India or Remote).",
        "",
        "Apply using the URLs below:",
        "",
    ]
    items: list[str] = []
    for index, job in enumerate(jobs, start=1):
        plain_lines.append(f"{index}. {job.company} — {job.role} — {job.location}")
        plain_lines.append(f"   {job.application_url}")
        plain_lines.append("")
        company = html.escape(job.company)
        role = html.escape(job.role)
        location = html.escape(job.location)
        url = html.escape(job.application_url, quote=True)
        items.append(
            "<li>"
            f"<strong>{company}</strong> — {role} — {location}<br>"
            f'<a href="{url}">{html.escape(job.application_url)}</a>'
            "</li>"
        )

    html_body = (
        "<p>Junior QA Engineer / Manual Tester openings in India or Remote.</p>"
        f"<ol>{''.join(items)}</ol>"
    )
    return "\n".join(plain_lines), html_body
