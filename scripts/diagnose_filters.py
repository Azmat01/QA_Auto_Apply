"""Count how filters drop QA jobs on a sample of live boards."""

from __future__ import annotations

from qa_auto_apply import greenhouse
from qa_auto_apply.config import load_settings
from qa_auto_apply.filters import (
    compile_keyword_regex,
    is_junior_role,
    matches_keywords,
    matches_location,
    title_is_senior,
)

SAMPLE = [
    ("Stripe", "stripe"),
    ("GitLab", "gitlab"),
    ("Elastic", "elastic"),
    ("Okta", "okta"),
    ("Coinbase", "coinbase"),
    ("Datadog", "datadog"),
    ("Cloudflare", "cloudflare"),
    ("MongoDB", "mongodb"),
    ("Airbnb", "airbnb"),
    ("Thoughtworks", "thoughtworks"),
]


def main() -> None:
    settings = load_settings()
    keyword_re = compile_keyword_regex(settings.get("keywords") or [])
    india_aliases = settings.get("india_location_aliases") or []
    http = {
        "timeout": 20,
        "max_retries": 2,
        "backoff_seconds": 1.0,
        "user_agent": "QA-Auto-Apply-diagnostic/1.0",
    }

    totals = {
        "fetched": 0,
        "qa_title": 0,
        "qa_location": 0,
        "qa_not_senior": 0,
        "qa_junior": 0,
    }
    examples_location: list[str] = []
    examples_blocked_junior: list[str] = []

    for name, token in SAMPLE:
        jobs = greenhouse.fetch_jobs(name, token, **http)
        totals["fetched"] += len(jobs)
        for job in jobs:
            if not matches_keywords(job.role, keyword_re):
                continue
            totals["qa_title"] += 1
            if not matches_location(job.location, india_aliases=india_aliases):
                continue
            totals["qa_location"] += 1
            label = f"{job.company} | {job.role} | {job.location}"
            if len(examples_location) < 8:
                examples_location.append(label)
            if title_is_senior(job.role):
                continue
            totals["qa_not_senior"] += 1
            if is_junior_role(job.role, job.description):
                totals["qa_junior"] += 1
            elif len(examples_blocked_junior) < 8:
                examples_blocked_junior.append(label)

    print("SAMPLE_COMPANIES", len(SAMPLE))
    print("FETCHED", totals["fetched"])
    print("QA_TITLE", totals["qa_title"])
    print("QA_AND_INDIA_OR_REMOTE", totals["qa_location"])
    print("QA_LOCATION_NOT_SENIOR_TITLE", totals["qa_not_senior"])
    print("QA_LOCATION_JUNIOR_REQUIRED", totals["qa_junior"])
    print("--- examples that pass location ---")
    for row in examples_location:
        print(row)
    print("--- examples blocked only by junior requirement ---")
    for row in examples_blocked_junior:
        print(row)


if __name__ == "__main__":
    main()
