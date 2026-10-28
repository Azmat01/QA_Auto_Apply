"""Greenhouse Job Board API client (public, unauthenticated GET)."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from qa_auto_apply.http_client import HttpError, get_json
from qa_auto_apply.models import JobListing
from qa_auto_apply.textutil import html_to_text

logger = logging.getLogger("qa_auto_apply.greenhouse")

GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"


def fetch_jobs(
    company_name: str,
    board_token: str,
    *,
    timeout: float,
    max_retries: int,
    backoff_seconds: float,
    user_agent: str,
) -> list[JobListing]:
    token = (board_token or "").strip()
    if not token:
        logger.warning("Skipping Greenhouse company with empty board token", extra={"company": company_name})
        return []

    url = GREENHOUSE_JOBS_URL.format(token=quote(token, safe=""))
    logger.info(
        "Fetching Greenhouse jobs for %s",
        company_name,
        extra={"company": company_name, "source": "greenhouse", "url": url},
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
            "Greenhouse request failed",
            extra={"company": company_name, "source": "greenhouse", "url": url},
        )
        return []

    if payload is None:
        logger.warning(
            "No Greenhouse board for token",
            extra={"company": company_name, "source": "greenhouse", "url": url},
        )
        return []

    jobs = _extract_jobs(payload)
    listings: list[JobListing] = []
    for job in jobs:
        listing = _to_listing(company_name, job)
        if listing:
            listings.append(listing)
    logger.info(
        "Fetched %s Greenhouse jobs for %s",
        len(listings),
        company_name,
        extra={
            "company": company_name,
            "source": "greenhouse",
            "fetched": len(listings),
        },
    )
    return listings


def _extract_jobs(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        jobs = payload.get("jobs") or []
        return [job for job in jobs if isinstance(job, dict)]
    if isinstance(payload, list):
        return [job for job in payload if isinstance(job, dict)]
    return []


def _to_listing(company_name: str, job: dict[str, Any]) -> JobListing | None:
    title = str(job.get("title") or "").strip()
    apply_url = str(job.get("absolute_url") or "").strip()
    if not title or not apply_url:
        return None

    location = ""
    raw_location = job.get("location")
    if isinstance(raw_location, dict):
        location = str(raw_location.get("name") or "").strip()
    elif isinstance(raw_location, str):
        location = raw_location.strip()

    if not location:
        offices = job.get("offices") or []
        names: list[str] = []
        for office in offices:
            if not isinstance(office, dict):
                continue
            office_name = str(office.get("name") or "").strip()
            office_location = str(office.get("location") or "").strip()
            names.append(office_location or office_name)
        location = ", ".join(part for part in names if part)

    job_id = str(job.get("id") or "")
    description = html_to_text(str(job.get("content") or ""))
    return JobListing(
        company=company_name,
        role=title,
        location=location or "Not specified",
        application_url=apply_url,
        source="greenhouse",
        job_id=job_id,
        description=description,
    )
