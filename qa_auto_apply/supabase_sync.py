"""Push matched jobs into the Supabase job_postings table for the GitHub Pages dashboard."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from qa_auto_apply.models import JobListing

logger = logging.getLogger("qa_auto_apply.supabase_sync")


class SupabaseSyncError(RuntimeError):
    pass


def sync_jobs_to_supabase(
    jobs: list[JobListing],
    *,
    url: str | None = None,
    api_key: str | None = None,
    table: str = "job_postings",
) -> int:
    """Insert new jobs and refresh metadata for existing URLs.

    Preserves existing ``is_applied`` values. Returns the number of rows touched.
    No-ops (returns 0) when credentials are missing.
    """
    base_url = (url or os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (
        api_key
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()
    table_name = (os.getenv("SUPABASE_TABLE") or table or "job_postings").strip()

    if not base_url or not key:
        logger.info("Supabase credentials not set; skipping dashboard sync")
        return 0

    if "://" not in base_url or base_url.startswith("https//"):
        raise SupabaseSyncError(
            f"Invalid SUPABASE_URL {base_url!r}. Expected https://PROJECT.supabase.co"
        )

    if not jobs:
        logger.info("No jobs to sync to Supabase")
        return 0

    today = datetime.now(timezone.utc).date().isoformat()
    payload: list[dict[str, Any]] = []
    for job in jobs:
        apply_url = (job.application_url or "").strip()
        if not apply_url:
            continue
        title = job.role.strip() or "Untitled role"
        if job.company:
            title = f"{job.company} — {title}"
        description_parts = [part for part in (job.location, job.description) if part]
        payload.append(
            {
                "title": title,
                "url": apply_url,
                "description": " | ".join(description_parts)[:4000],
                "date": today,
            }
        )

    if not payload:
        return 0

    existing = _fetch_rows(base_url, key, table_name)
    by_url = {str(row["url"]): str(row["id"]) for row in existing if row.get("url") and row.get("id")}
    placeholders = [
        str(row["id"])
        for row in existing
        if "example.com" in str(row.get("url") or "").lower()
    ]

    inserted = 0
    updated = 0

    for row in payload:
        apply_url = row["url"]
        existing_id = by_url.get(apply_url)
        if existing_id:
            _patch_job(base_url, key, table_name, existing_id, row)
            updated += 1
            continue

        if placeholders:
            placeholder_id = placeholders.pop(0)
            _patch_job(base_url, key, table_name, placeholder_id, {**row, "replace_url": True})
            by_url[apply_url] = placeholder_id
            updated += 1
            continue

        _insert_job(base_url, key, table_name, row)
        inserted += 1

    logger.info(
        "Synced jobs to Supabase (%s inserted, %s updated)",
        inserted,
        updated,
        extra={"matched": inserted + updated},
    )
    return inserted + updated


def _headers(key: str, *, prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(
    url: str,
    *,
    key: str,
    method: str = "GET",
    body: bytes | None = None,
    prefer: str | None = None,
) -> Any:
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=_headers(key, prefer=prefer),
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            if not raw:
                return None
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SupabaseSyncError(f"Supabase HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SupabaseSyncError(f"Supabase network error: {exc}") from exc


def _fetch_rows(base_url: str, key: str, table: str) -> list[dict[str, Any]]:
    endpoint = (
        f"{base_url}/rest/v1/{urllib.parse.quote(table)}"
        f"?select=id,url&limit=1000"
    )
    rows = _request(endpoint, key=key) or []
    return [row for row in rows if isinstance(row, dict)]


def _insert_job(base_url: str, key: str, table: str, row: dict[str, Any]) -> None:
    endpoint = f"{base_url}/rest/v1/{urllib.parse.quote(table)}"
    payload = {
        "title": row["title"],
        "url": row["url"],
        "description": row.get("description") or "",
        "date": row["date"],
        "is_applied": False,
    }
    _request(
        endpoint,
        key=key,
        method="POST",
        body=json.dumps(payload).encode("utf-8"),
        prefer="return=minimal",
    )


def _patch_job(
    base_url: str,
    key: str,
    table: str,
    job_id: str,
    row: dict[str, Any],
) -> None:
    endpoint = (
        f"{base_url}/rest/v1/{urllib.parse.quote(table)}"
        f"?id=eq.{urllib.parse.quote(job_id)}"
    )
    payload = {
        "title": row["title"],
        "description": row.get("description") or "",
        "date": row["date"],
    }
    if row.get("replace_url"):
        payload["url"] = row["url"]
        payload["is_applied"] = False
    _request(
        endpoint,
        key=key,
        method="PATCH",
        body=json.dumps(payload).encode("utf-8"),
        prefer="return=minimal",
    )
