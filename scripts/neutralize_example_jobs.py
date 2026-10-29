"""Replace example.com placeholders with a clear notice until real jobs sync."""

from __future__ import annotations

import json
import urllib.request

KEY = "sb_publishable_zxQP2aJ4Z79OuDo-0YvWPA_MwDBWBu_"
BASE = "https://gstjnmduuevtwlybaldm.supabase.co/rest/v1/job_postings"
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def main() -> None:
    req = urllib.request.Request(BASE + "?select=id,url,title", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as response:
        rows = json.loads(response.read().decode())

    for row in rows:
        if "example.com" not in str(row.get("url") or "").lower():
            continue
        payload = {
            "title": "No live junior QA openings in the latest scan",
            "url": "https://github.com/Azmat01/QA_Auto_Apply#job-dashboard-github-pages--supabase",
            "description": (
                "example.com links were placeholders only. "
                "Open posting now goes to the project README. "
                "Real Greenhouse/Lever apply URLs will appear after the next successful sync."
            ),
        }
        patch = urllib.request.Request(
            f"{BASE}?id=eq.{row['id']}",
            data=json.dumps(payload).encode("utf-8"),
            method="PATCH",
            headers=HEADERS,
        )
        with urllib.request.urlopen(patch, timeout=20) as response:
            print("updated", row["id"], response.read().decode()[:120])


if __name__ == "__main__":
    main()
