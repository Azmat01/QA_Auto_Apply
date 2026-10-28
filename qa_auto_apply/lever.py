"""Lever Postings API client (public, unauthenticated GET)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from qa_auto_apply.http_client import HttpError, get_json
from qa_auto_apply.models import JobListing
from qa_auto_apply.textutil import html_to_text

logger = logging.getLogger("qa_auto_apply.lever")

LEVER_US_URL = "https://api.lever.co/v0/postings/{site}?mode=json"
LEVER_EU_URL = "https://api.eu.lever.co/v0/postings/{site}?mode=json"


def fetch_jobs(
    company_name: str,
    site: str,
    *,
    timeout: float,
    max_retries: int,
    backoff_seconds: float,
    user_agent: str,
) -> list[JobListing]:
    slug = (site or "").strip()
    if not slug:
        logger.warning("Skipping Lever company with empty site slug", extra={"company": company_name})
        return []

    encoded = quote(slug, safe="")
    urls = [
        LEVER_US_URL.format(site=encoded),
        LEVER_EU_URL.format(site=encoded),
    ]

    payload = None
    last_url = urls[0]
    for url in urls:
        last_url = url
        logger.info(
            "Fetching Lever jobs for %s",
            company_name,
            extra={"company": company_name, "source": "lever", "url": url},
        )
        try:
            payload = get_json(
                url,
                timeout=timeout,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
                user_agent=user_agent,
                accept_404=True,
            )
        except HttpError:
            logger.exception(
                "Lever request failed",
                extra={"company": company_name, "source": "lever", "url": url},
            )
            payload = None
            continue
        if payload is not None:
            break

    if payload is None:
        logger.warning(
            "No Lever postings for site",
            extra={"company": company_name, "source": "lever", "url": last_url},
        )
        return []

    jobs = payload if isinstance(payload, list) else []
    listings: list[JobListing] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        listing = _to_listing(company_name, job)
        if listing:
            listings.append(listing)

    logger.info(
        "Fetched %s Lever jobs for %s",
        len(listings),
        company_name,
        extra={"company": company_name, "source": "lever", "fetched": len(listings)},
    )
    return listings


def _to_listing(company_name: str, job: dict[str, Any]) -> JobListing | None:
    title = str(job.get("text") or job.get("title") or "").strip()
    apply_url = str(job.get("applyUrl") or job.get("hostedUrl") or "").strip()
    if not title or not apply_url:
        return None

    categories = job.get("categories") if isinstance(job.get("categories"), dict) else {}
    location_parts = [
        str(categories.get("location") or "").strip(),
        str(job.get("country") or "").strip(),
        str(job.get("workplaceType") or "").strip(),
    ]
    location = ", ".join(part for part in location_parts if part) or "Not specified"

    return JobListing(
        company=company_name,
        role=title,
        location=location,
        application_url=apply_url,
        source="lever",
        job_id=str(job.get("id") or ""),
        description=_lever_description(job),
    )


def _lever_description(job: dict[str, Any]) -> str:
    parts: list[str] = []
    plain = str(job.get("descriptionPlain") or "").strip()
    if plain:
        parts.append(plain)
    else:
        parts.append(html_to_text(str(job.get("description") or "")))
    lists = job.get("lists") or []
    if isinstance(lists, list):
        for section in lists:
            if not isinstance(section, dict):
                continue
            parts.append(str(section.get("text") or "").strip())
            parts.append(html_to_text(str(section.get("content") or "")))
    return html_to_text(" ".join(part for part in parts if part))


def extra_location_fields(job: dict[str, Any]) -> tuple[str, str]:
    """Return (workplace_type, country) for location matching."""
    workplace = str(job.get("workplaceType") or "")
    country = str(job.get("country") or "")
    return workplace, country
