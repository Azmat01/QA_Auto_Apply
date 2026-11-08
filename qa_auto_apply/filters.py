"""Keyword, remote/WFH location, and 0-1 year / internship matching."""

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
        "bangladesh",
        "sri lanka",
        "nepal",
        "maldives",
        "bhutan",
    }
)

DEFAULT_BLOCKED_COUNTRIES = frozenset(
    {
        "pakistan",
        "egypt",
        "argentina",
        "pk",
        "eg",
        "ar",
        "karachi",
        "lahore",
        "islamabad",
        "cairo",
        "alexandria",
        "buenos aires",
    }
)

# Country / region tokens that are acceptable when a remote role names a place.
_REGION_PATTERNS: dict[str, tuple[str, ...]] = {
    "europe": (
        r"\beurope\b",
        r"\beu\b",
        r"\buk\b",
        r"\bunited\s+kingdom\b",
        r"\bengland\b",
        r"\bscotland\b",
        r"\bireland\b",
        r"\bgermany\b",
        r"\bfrance\b",
        r"\bnetherlands\b",
        r"\bdutch\b",
        r"\bspain\b",
        r"\bitaly\b",
        r"\bportugal\b",
        r"\bpoland\b",
        r"\bsweden\b",
        r"\bnorway\b",
        r"\bdenmark\b",
        r"\bfinland\b",
        r"\bbelgium\b",
        r"\baustria\b",
        r"\bswitzerland\b",
        r"\bromania\b",
        r"\bczech\b",
        r"\bhungary\b",
        r"\bgreece\b",
        r"\bemea\b",
    ),
    "americas": (
        r"\bamerica\b",
        r"\bamericas\b",
        r"\bunited\s+states\b",
        r"\busa\b",
        r"\bu\.?s\.?\b",
        r"\bcanada\b",
        r"\bmexico\b",
        r"\bbrazil\b",
        r"\bcolombia\b",
        r"\bchile\b",
        r"\bperu\b",
        r"\blatin\s+america\b",
        r"\bnorth\s+america\b",
        r"\bsouth\s+america\b",
    ),
    "arabian": (
        r"\barab\b",
        r"\bgulf\b",
        r"\bgcc\b",
        r"\bu\.?a\.?e\.?\b",
        r"\bunited\s+arab\s+emirates\b",
        r"\bdubai\b",
        r"\babu\s+dhabi\b",
        r"\bsaudi\b",
        r"\bksa\b",
        r"\briyadh\b",
        r"\bqatar\b",
        r"\bdoha\b",
        r"\bkuwait\b",
        r"\bbahrain\b",
        r"\boman\b",
        r"\bjordan\b",
        r"\bmiddle\s+east\b",
    ),
    "middle_east": (
        r"\bmiddle\s+east\b",
        r"\bgulf\b",
        r"\bgcc\b",
    ),
    "southeast_asia": (
        r"\bsouth[\s-]?east\s+asia\b",
        r"\bsoutheast\s+asia\b",
        r"\basean\b",
        r"\bsingapore\b",
        r"\bmalaysia\b",
        r"\bindonesia\b",
        r"\bthailand\b",
        r"\bvietnam\b",
        r"\bphilippines\b",
        r"\bcambodia\b",
    ),
    "south_asia": (
        r"\bsouth\s+asia\b",
        r"\bindia\b",
        r"\bbangladesh\b",
        r"\bsri\s+lanka\b",
        r"\bnepal\b",
        r"\bmaldives\b",
        r"\bbhutan\b",
    ),
    "australia": (
        r"\baustralia\b",
        r"\baustralian\b",
        r"\bnew\s+zealand\b",
        r"\banz\b",
        r"\bsydney\b",
        r"\bmelbourne\b",
        r"\bbrisbane\b",
        r"\bauckland\b",
    ),
}

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
    r"\bqa\s+intern(?:ship)?\b",
    r"\btest(?:ing)?\s+intern(?:ship)?\b",
    r"\bsdet\s+intern(?:ship)?\b",
    r"\bquality\s+intern(?:ship)?\b",
    r"\bintern(?:ship)?\s+(?:qa|sdet|tester|testing|quality)\b",
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
    | \b0\s*[-–to]+\s*1\s*years?\b
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
    | \b0\s*[-–to]+\s*1\s*years?\b
    | \b0\s*[-–]\s*12\s*months?\b
    | \b0\s*years?\b
    | \b1\s*year\b
    | \b(?:0\s*[-–to]+\s*)?6\s*months?\b
    | \bno\s+(?:prior\s+)?experience\s+required\b
    | \bless\s+than\s+(?:one|1)\s+years?\b
    | \bminimum\s+(?:0|1)\s*years?\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

_INTERNSHIP_RE = re.compile(
    r"\b(?:intern|internship|trainee|apprentice|co-?op)\b",
    re.IGNORECASE,
)


def compile_keyword_regex(extra_keywords: Iterable[str] | None = None) -> re.Pattern[str]:
    patterns = list(_KEYWORD_PATTERNS)
    for keyword in extra_keywords or []:
        token = keyword.strip()
        if not token:
            continue
        # Bare "Internship" alone is too broad; keep QA/test-related extras only.
        if token.lower() in {"internship", "intern"}:
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


def is_internship(title: str, description: str = "") -> bool:
    return bool(_INTERNSHIP_RE.search(title or "") or _INTERNSHIP_RE.search(description or ""))


def is_junior_role(title: str, description: str = "") -> bool:
    """Junior/intern/0-1y if title looks junior, or body does and title is not senior."""
    if title_is_senior(title):
        return False
    if title_looks_junior(title) or is_internship(title, description):
        return True
    return description_looks_junior(description)


def matches_location(
    location: str,
    *,
    workplace_type: str = "",
    country: str = "",
    india_aliases: Iterable[str] | None = None,
    require_remote: bool = True,
    blocked_countries: Iterable[str] | None = None,
    allowed_regions: Iterable[str] | None = None,
    allow_remote: bool = True,
    allow_india: bool = True,
) -> bool:
    """Return True for remote/WFH roles in allowed regions, excluding blocked countries."""
    haystack = " ".join(part for part in (location, workplace_type, country) if part).lower()
    if not haystack.strip():
        return False

    if _is_blocked(haystack, blocked_countries):
        return False

    remote = allow_remote and _is_remote(haystack)
    if require_remote and not remote:
        return False

    # Pure remote / worldwide / WFH with no blocked country is OK.
    if remote and not _has_explicit_geo(haystack):
        return True

    if remote and _matches_allowed_region(haystack, allowed_regions, india_aliases):
        return True

    # Non-remote path only when require_remote is False (legacy).
    if not require_remote:
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
    """Lower tuples sort first: internship, then junior title, then company/role."""
    internship_priority = 0 if is_internship(listing.role, listing.description) else 1
    title_priority = 0 if title_looks_junior(listing.role) else 1
    return (
        internship_priority,
        title_priority,
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
        r"\bwork\s+from\s+anywhere\b",
        r"\bfully\s+remote\b",
        r"\bhome[\s-]?based\b",
    )
    return any(re.search(marker, text) for marker in remote_markers)


def _is_blocked(text: str, blocked_countries: Iterable[str] | None) -> bool:
    blocked = DEFAULT_BLOCKED_COUNTRIES.union(
        str(item).strip().lower() for item in (blocked_countries or []) if str(item).strip()
    )
    for item in blocked:
        if len(item) <= 2:
            if re.search(rf"(?:^|[\s,/(]){re.escape(item)}(?:$|[\s,)/])", text):
                return True
        elif re.search(rf"\b{re.escape(item)}\b", text):
            return True
    return False


def _has_explicit_geo(text: str) -> bool:
    # Rough check: contains a known country/region word beyond "remote".
    cleaned = re.sub(r"\b(?:remote|wfh|work|from|home|anywhere|worldwide|distributed|hybrid)\b", " ", text)
    return bool(re.search(r"[a-z]{3,}", cleaned))


def _matches_allowed_region(
    text: str,
    allowed_regions: Iterable[str] | None,
    india_aliases: Iterable[str] | None,
) -> bool:
    regions = [str(r).strip().lower() for r in (allowed_regions or []) if str(r).strip()]
    if not regions:
        regions = list(_REGION_PATTERNS.keys())

    for region in regions:
        key = region.replace("-", "_").replace(" ", "_")
        if key == "arabian":
            key = "arabian"
        patterns = _REGION_PATTERNS.get(key) or _REGION_PATTERNS.get(region)
        if patterns and any(re.search(pat, text) for pat in patterns):
            return True
        if key in {"south_asia", "india"} and _is_india(text, india_aliases):
            return True
    return False


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
    experience_mode: str = "junior_only",
    require_remote: bool = True,
    blocked_countries: Iterable[str] | None = None,
    allowed_regions: Iterable[str] | None = None,
) -> bool:
    """Filter a listing for remote junior/intern QA roles in allowed regions."""
    if not matches_keywords(listing.role, keyword_re):
        return False

    if not matches_location(
        listing.location,
        workplace_type=workplace_type,
        country=country,
        india_aliases=india_aliases,
        require_remote=require_remote,
        blocked_countries=blocked_countries,
        allowed_regions=allowed_regions,
    ):
        return False

    mode = (experience_mode or "junior_only").strip().lower()
    if mode == "any":
        return not title_is_senior(listing.role)
    if mode == "exclude_senior":
        return not title_is_senior(listing.role)
    # junior_only (preferred for 0-1 years + internships)
    return is_junior_role(listing.role, listing.description)
