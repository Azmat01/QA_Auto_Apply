"""Keyword, location, and junior-experience matching."""

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
    r"\bmanual\s+tester\b",
    r"\bmanual\s+qa\b",
    r"\bqa\s+tester\b",
    r"\bquality\s+analyst\b",
    r"\btest\s+analyst\b",
    r"\bmanual\s+test(?:ing)?\b",
]

_SENIOR_TITLE_RE = re.compile(
    r"""
    \b(?:senior|sr\.?|staff|principal|lead|manager|director|head|architect)\b
    | \b(?:[3-9]|1\d)\s*\+\s*years?\b
    | \b(?:[3-9]|1\d)\s*[-–]\s*\d+\s*years?\b
    | \b(?:[3-9]|1\d)\s*years?\s*(?:\+|plus|experience)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_JUNIOR_TITLE_RE = re.compile(
    r"""
    \b(?:fresher|intern|internship|trainee|apprentice|graduate|campus)\b
    | \bjunior\b
    | \bassociate\b
    | \bentry[\s-]?level\b
    | \bnew\s+grad(?:uate)?\b
    | \b0\s*[-–to]+\s*[12]\s*years?\b
    | \b0\s*years?\b
    | \b1\s*year\b
    | \b(?:0\s*[-–to]+\s*)?6\s*months?\b
    | \bfreshers?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_JUNIOR_DESCRIPTION_RE = re.compile(
    r"""
    \b(?:fresher|freshers|intern|internship|trainee|apprentice)\b
    | \bjunior\b
    | \bentry[\s-]?level\b
    | \bnew\s+grad(?:uate)?\b
    | \bfresh\s+graduate\b
    | \bcampus\s+(?:hire|hiring|recruit(?:ment)?|graduate|drive)\b
    | \bassociate\s+(?:qa|quality|test|sdet|engineer|tester)\b
    | \b0\s*[-–to]+\s*[12]\s*years?\b
    | \b0\s*[-–]\s*12\s*months?\b
    | \b0\s*years?\b
    | \b1\s*year\b
    | \b(?:0\s*[-–to]+\s*)?6\s*months?\b
    | \bno\s+(?:prior\s+)?experience\s+required\b
    | \bless\s+than\s+(?:one|1|two|2)\s+years?\b
    | \bminimum\s+(?:0|1)\s*years?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


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


def title_is_senior(title: str) -> bool:
    return bool(title and _SENIOR_TITLE_RE.search(title))


def title_looks_junior(title: str) -> bool:
    return bool(title and _JUNIOR_TITLE_RE.search(title))


def description_looks_junior(description: str) -> bool:
    return bool(description and _JUNIOR_DESCRIPTION_RE.search(description))


def is_junior_role(title: str, description: str = "") -> bool:
    """Junior if the title looks junior, or the body does and the title is not senior."""
    if title_is_senior(title):
        return False
    if title_looks_junior(title):
        return True
    return description_looks_junior(description)


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


def location_is_india(
    location: str,
    *,
    india_aliases: Iterable[str] | None = None,
) -> bool:
    return _is_india(location.lower(), india_aliases)


def rank_key(listing: JobListing, india_aliases: Iterable[str] | None = None) -> tuple:
    """Lower tuples sort first: title junior, then India, then company/role."""
    title_priority = 0 if title_looks_junior(listing.role) else 1
    india_priority = 0 if location_is_india(listing.location, india_aliases=india_aliases) else 1
    return (
        title_priority,
        india_priority,
        listing.company.lower(),
        listing.role.lower(),
    )


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
    if not matches_location(
        listing.location,
        workplace_type=workplace_type,
        country=country,
        india_aliases=india_aliases,
    ):
        return False
    return is_junior_role(listing.role, listing.description)
