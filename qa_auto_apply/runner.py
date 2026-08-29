"""Orchestrate ATS fetches, filtering, export, and optional email."""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from qa_auto_apply.config import ROOT_DIR, load_companies, load_settings
from qa_auto_apply.exporters import save_csv, save_digest, save_json
from qa_auto_apply.filters import compile_keyword_regex, keep_listing
from qa_auto_apply import greenhouse, lever
from qa_auto_apply.logging_setup import setup_logging
from qa_auto_apply.models import JobListing
from qa_auto_apply.notifier import send_digest_email

logger = logging.getLogger("qa_auto_apply.runner")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find QA / SDET jobs from public Greenhouse and Lever APIs.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT_DIR / "output"),
        help="Directory for CSV, JSON, and Markdown digest files.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send the digest over SMTP when SMTP_USERNAME and SMTP_PASSWORD are set.",
    )
    parser.add_argument(
        "--notify-only",
        action="store_true",
        help="Skip fetching and only email the existing digest in --output-dir.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.log_level)

    try:
        settings = load_settings()
        companies = load_companies()
    except Exception:
        logger.exception("Failed to load configuration")
        return 1

    notify_email = str(settings.get("notify_email") or "azmatsparrow@gmail.com")
    notify_label = str(settings.get("notify_label") or "QA-auto-apply")
    output_dir = Path(args.output_dir)

    if args.notify_only:
        digest_path = output_dir / "digest.md"
        json_path = output_dir / "jobs.json"
        count = 0
        if json_path.is_file():
            try:
                count = int(json.loads(json_path.read_text(encoding="utf-8")).get("count") or 0)
            except (OSError, ValueError, TypeError):
                count = 0
        return _maybe_email(args.send_email, digest_path, notify_email, notify_label, count)

    keyword_re = compile_keyword_regex(settings.get("keywords") or [])
    india_aliases = settings.get("india_location_aliases") or []
    timeout = float(settings.get("request_timeout_seconds") or 20)
    max_retries = int(settings.get("max_retries") or 3)
    backoff = float(settings.get("retry_backoff_seconds") or 1.5)
    user_agent = str(settings.get("user_agent") or "QA-Auto-Apply/1.0")
    http_kwargs = {
        "timeout": timeout,
        "max_retries": max_retries,
        "backoff_seconds": backoff,
        "user_agent": user_agent,
    }

    matched: list[JobListing] = []
    seen: set[tuple[str, str, str]] = set()
    errors = 0

    for company in companies.get("greenhouse") or []:
        if not isinstance(company, dict):
            continue
        name = str(company.get("name") or company.get("board_token") or "").strip()
        token = str(company.get("board_token") or "").strip()
        try:
            listings = greenhouse.fetch_jobs(name, token, **http_kwargs)
        except Exception:
            errors += 1
            logger.exception("Unexpected Greenhouse error", extra={"company": name, "source": "greenhouse"})
            continue
        _collect(listings, matched, seen, keyword_re, india_aliases)
        time.sleep(0.15)

    for company in companies.get("lever") or []:
        if not isinstance(company, dict):
            continue
        name = str(company.get("name") or company.get("site") or "").strip()
        site = str(company.get("site") or "").strip()
        try:
            listings = lever.fetch_jobs(name, site, **http_kwargs)
        except Exception:
            errors += 1
            logger.exception("Unexpected Lever error", extra={"company": name, "source": "lever"})
            continue
        _collect(listings, matched, seen, keyword_re, india_aliases)
        time.sleep(0.15)

    matched.sort(key=lambda job: (job.company.lower(), job.role.lower()))

    output_dir = Path(args.output_dir)
    csv_path = save_csv(matched, output_dir / "jobs.csv")
    json_path = save_json(matched, output_dir / "jobs.json")
    digest_path = save_digest(
        matched,
        output_dir / "digest.md",
        email=notify_email,
        label=notify_label,
    )

    logger.info(
        "Wrote results",
        extra={"matched": len(matched), "url": str(output_dir)},
    )
    logger.info("CSV: %s", csv_path)
    logger.info("JSON: %s", json_path)
    logger.info("Digest: %s", digest_path)
    logger.info("Companies with hard failures: %s", errors)

    return _maybe_email(args.send_email, digest_path, notify_email, notify_label, len(matched))


def _maybe_email(
    send_email: bool,
    digest_path: Path,
    notify_email: str,
    notify_label: str,
    job_count: int,
) -> int:
    if not send_email:
        return 0
    try:
        send_digest_email(
            digest_path,
            to_address=notify_email,
            subject=f"[{notify_label}] {job_count} QA jobs (India / Remote)",
            job_count=job_count,
        )
    except Exception:
        logger.exception("Email notification failed")
        return 1
    return 0


def _collect(
    listings: list[JobListing],
    matched: list[JobListing],
    seen: set[tuple[str, str, str]],
    keyword_re,
    india_aliases,
) -> None:
    for listing in listings:
        if not keep_listing(listing, keyword_re, india_aliases=india_aliases):
            continue
        identity = listing.identity()
        if identity in seen:
            continue
        seen.add(identity)
        matched.append(listing)
        logger.info(
            "Matched job",
            extra={
                "company": listing.company,
                "role": listing.role,
                "location": listing.location,
                "url": listing.application_url,
                "matched": True,
            },
        )
