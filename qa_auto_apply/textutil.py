"""Plain-text helpers for ATS HTML job descriptions."""

from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")


def html_to_text(raw: str, *, limit: int = 8000) -> str:
    """Strip tags and collapse whitespace so experience filters can scan the body."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text).strip()
    if limit and len(text) > limit:
        return text[:limit]
    return text
