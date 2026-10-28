"""Write matched jobs to CSV, JSON, and a Markdown digest."""

from __future__ import annotations

import csv
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
        f"# Junior QA / Manual Tester digest ({generated})",
        "",
        f"- Label: `{label}`",
        f"- Notify: {email}",
        f"- Listed: **{len(jobs)}** (top 10 of {scanned} junior matches)",
        "",
    ]
    if not jobs:
        lines.append(
            "No matching junior QA Engineer / Manual Tester roles were found for India or Remote."
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
