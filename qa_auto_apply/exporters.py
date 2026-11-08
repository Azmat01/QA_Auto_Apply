"""Write matched jobs to CSV, JSON, and a Markdown digest."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from qa_auto_apply.models import JobListing

CSV_FIELDS = ("Company Name", "Role", "Location", "Application URL")


def save_csv(jobs: list[JobListing], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_FIELDS))
        writer.writeheader()
        for job in jobs:
            writer.writerow(job.to_row())
    return path


def save_json(jobs: list[JobListing], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(jobs),
        "jobs": [job.to_row() for job in jobs],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def save_dashboard_json(jobs: list[JobListing], path: Path) -> Path:
    """Write the GitHub Pages dashboard feed (docs/data/jobs.json)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    rows = []
    for job in jobs:
        title = job.role.strip() or "Untitled role"
        if job.company:
            title = f"{job.company} — {title}"
        description = " | ".join(part for part in (job.location, job.description) if part)
        apply_url = (job.application_url or "").strip()
        rows.append(
            {
                "id": _stable_id(apply_url or title),
                "title": title,
                "url": apply_url,
                "description": description[:4000],
                "date": today,
                "is_applied": False,
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "source": "job_finder",
        "jobs": rows,
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def _stable_id(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return digest[:16]


def save_digest(
    jobs: list[JobListing],
    path: Path,
    *,
    email: str,
    label: str,
    pool_size: int | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    scanned = pool_size if pool_size is not None else len(jobs)
    lines = [
        f"# QA / Manual Tester digest ({generated})",
        "",
        f"- Label: `{label}`",
        f"- Notify: {email}",
        f"- Listed: **{len(jobs)}** (top 10 of {scanned} matches)",
        "",
    ]
    if not jobs:
        lines.append(
            "No matching remote QA / Manual Tester / internship roles (0-1 years) were found "
            "on the configured Greenhouse/Lever boards for allowed regions."
        )
    else:
        lines.extend(
            [
                "| # | Company Name | Role | Location | Application URL |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for index, job in enumerate(jobs, start=1):
            role = _md_cell(job.role)
            location = _md_cell(job.location)
            company = _md_cell(job.company)
            url = job.application_url.replace("|", "\\|")
            lines.append(f"| {index} | {company} | {role} | {location} | {url} |")
        lines.append("")
        lines.append("Apply links:")
        for index, job in enumerate(jobs, start=1):
            lines.append(f"{index}. [{_md_cell(job.company)} — {_md_cell(job.role)}]({job.application_url})")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
