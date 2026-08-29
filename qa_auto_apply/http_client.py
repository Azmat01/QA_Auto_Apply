"""HTTP helper with timeouts, retries, and structured error handling."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("qa_auto_apply.http")

TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class HttpError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, url: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


def get_json(
    url: str,
    *,
    timeout: float = 20,
    max_retries: int = 3,
    backoff_seconds: float = 1.5,
    user_agent: str = "QA-Auto-Apply/1.0",
    accept_404: bool = False,
) -> Any | None:
    """GET JSON. Returns None for 404 when accept_404 is True."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
        method="GET",
    )
    last_error: Exception | None = None
    attempts = max(1, max_retries)

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            last_error = exc
            if status == 404 and accept_404:
                logger.warning(
                    "Resource not found; skipping",
                    extra={"url": url, "status_code": status},
                )
                return None
            if status in TRANSIENT_STATUS_CODES and attempt < attempts:
                sleep_for = backoff_seconds * attempt
                logger.warning(
                    "Transient HTTP error, retrying",
                    extra={"url": url, "status_code": status},
                )
                time.sleep(sleep_for)
                continue
            raise HttpError(
                f"HTTP {status} for {url}",
                status_code=status,
                url=url,
            ) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts:
                sleep_for = backoff_seconds * attempt
                logger.warning(
                    "Network or parse error, retrying: %s",
                    exc,
                    extra={"url": url, "status_code": None},
                )
                time.sleep(sleep_for)
                continue
            raise HttpError(f"Failed to fetch {url}: {exc}", url=url) from exc

    raise HttpError(f"Failed to fetch {url}: {last_error}", url=url)
