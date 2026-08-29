"""Keyword and location matching for QA / SDET roles in India or Remote."""

from __future__ import annotations

import re
from typing import Iterable

from qa_auto_apply.models import JobListing

DEFAULT_INDIA_ALIASES = frozenset(
    {
        "india",
        "indian",
        "bharat",
        "bangalore",
        "bengaluru",
        "hyderabad",
        "pune",
        "chennai",
        "mumbai",
        "delhi",
        "noida",
        "gurgaon",
        "gurugram",
        "kolkata",
        "ahmedabad",
        "jaipur",
        "kochi",
        "cochin",
        "thiruvananthapuram",
        "trivandrum",
        "coimbatore",
        "indore",
        "nagpur",
        "mysore",
        "mysuru",
        "ncr",
    }
)

# "QA" must be a standalone token so titles like "EQUAL" or "SQUARE" do not match.
_KEYWORD_PATTERNS = [
    r"\bqa\b",
    r"\bsdet\b",
    r"\bsoftware\s+development\s+engineer\s+in\s+test\b",
    r"\bautomation\s+qa\b",
    r"\btest\s+engineer\b",
    r"\bquality\s+assurance\b",
    r"\bquality\s+engineer\b",
    r"\bsoftware\s+test(?:ing)?\b",
    r"\btest\s+automation\b",
    r"\bautomation\s+tester\b",
    r"\bqa\s+engineer\b",
    r"\bqa\s+automation\b",
    r"\bquality\s+engineering\b",
]


def compile_keyword_regex(extra_keywords: Iterable[str] | None = None) -> re.Pattern[str]:
    patterns = list(_KEYWORD_PATTERNS)
    for keyword in extra_keywords or []:
        token = keyword.strip()
        if not token:
            continue
        escaped = re.escape(token)
        escaped = re.sub(r"\\ +", r"\\s+", escaped)
        patterns.append(rf"\b{escaped}\b")
    return re.compile("|".join(patterns), re.IGNORECASE)


def matches_keywords(title: str, keyword_re: re.Pattern[str]) -> bool:
    return bool(title and keyword_re.search(title))


def matches_location(
    location: str,
    *,
    workplace_type: str = "",
    country: str = "",
    india_aliases: Iterable[str] | None = None,
    allow_remote: bool = True,
    allow_india: bool = True,
) -> bool:
    """Return True when the posting is India-based or remote (including hybrid-remote)."""
    haystack = " ".join(part for part in (location, workplace_type, country) if part).lower()
    if not haystack.strip():
        return False

    if allow_remote and _is_remote(haystack):
        return True

    if allow_india and country.strip().upper() in {"IN", "IND"}:
        return True

    if allow_india and _is_india(haystack, india_aliases):
        return True

    return False


def _is_remote(text: str) -> bool:
    remote_markers = (
        r"\bremote\b",
        r"\bwork\s+from\s+home\b",
        r"\bwfh\b",
        r"\banywhere\b",
        r"\bdistributed\b",
        r"\bworldwide\b",
    )
    return any(re.search(marker, text) for marker in remote_markers)


def _is_india(text: str, india_aliases: Iterable[str] | None) -> bool:
    if re.search(r"\bindia\b", text):
        return True
    if re.search(r"(?:,\s*|/)\s*\bin\b\s*$", text):
        return True
    aliases = DEFAULT_INDIA_ALIASES.union(
        alias.lower() for alias in (india_aliases or []) if alias
    )
    return any(re.search(rf"\b{re.escape(alias)}\b", text) for alias in aliases)


def keep_listing(
    listing: JobListing,
    keyword_re: re.Pattern[str],
    *,
    workplace_type: str = "",
    country: str = "",
    india_aliases: Iterable[str] | None = None,
) -> bool:
    if not matches_keywords(listing.role, keyword_re):
        return False
    return matches_location(
        listing.location,
        workplace_type=workplace_type,
        country=country,
        india_aliases=india_aliases,
    )
