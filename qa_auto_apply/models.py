"""Shared job listing model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class JobListing:
    company: str
    role: str
    location: str
    application_url: str
    source: str
    job_id: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "Company Name": self.company,
            "Role": self.role,
            "Location": self.location,
            "Application URL": self.application_url,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def identity(self) -> tuple[str, str, str]:
        return (self.company.lower(), self.role.lower(), self.application_url.lower())
