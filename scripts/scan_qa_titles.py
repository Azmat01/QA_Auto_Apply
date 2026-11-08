"""Quick title-only scan across all configured Greenhouse boards."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from qa_auto_apply.config import load_companies, load_settings
from qa_auto_apply.filters import compile_keyword_regex, matches_keywords, matches_location, title_is_senior

ROOT = Path(__file__).resolve().parents[1]


def fetch_titles(token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QA-Auto-Apply-scan/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:  # noqa: BLE001
        return []
    jobs = payload.get("jobs") if isinstance(payload, dict) else payload
    return [job for job in jobs or [] if isinstance(job, dict)]


def main() -> None:
    settings = load_settings()
    companies = load_companies()
    keyword_re = compile_keyword_regex(settings.get("keywords") or [])
    aliases = settings.get("india_location_aliases") or []

    qa_all = []
    qa_loc = []
    qa_loc_mid = []
    dead = 0
    live = 0

    for company in companies.get("greenhouse") or []:
        name = company.get("name")
        token = company.get("board_token")
        jobs = fetch_titles(token)
        if not jobs:
            dead += 1
            continue
        live += 1
        for job in jobs:
            title = str(job.get("title") or "")
            if not matches_keywords(title, keyword_re):
                continue
            loc = ""
            raw = job.get("location")
            if isinstance(raw, dict):
                loc = str(raw.get("name") or "")
            apply_url = str(job.get("absolute_url") or "")
            row = f"{name} | {title} | {loc} | {apply_url}"
            qa_all.append(row)
            if matches_location(loc, india_aliases=aliases):
                qa_loc.append(row)
                if not title_is_senior(title):
                    qa_loc_mid.append(row)

    print("LIVE_BOARDS", live, "DEAD_OR_EMPTY", dead)
    print("QA_ANY_LOCATION", len(qa_all))
    print("QA_INDIA_OR_REMOTE", len(qa_loc))
    print("QA_INDIA_OR_REMOTE_NOT_SENIOR_TITLE", len(qa_loc_mid))
    print("--- mid-level / non-senior India-or-Remote QA ---")
    for row in qa_loc_mid[:20]:
        print(row)
    print("--- senior India-or-Remote QA ---")
    for row in qa_loc[:20]:
        if row not in qa_loc_mid:
            print(row)


if __name__ == "__main__":
    main()
