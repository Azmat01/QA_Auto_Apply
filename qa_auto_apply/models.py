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
    description: str = ""

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

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> JobListing:
        return cls(
            company=str(row.get("Company Name") or row.get("company") or "").strip(),
            role=str(row.get("Role") or row.get("role") or "").strip(),
            location=str(row.get("Location") or row.get("location") or "").strip(),
            application_url=str(
                row.get("Application URL") or row.get("application_url") or ""
            ).strip(),
            source=str(row.get("source") or "unknown"),
            job_id=str(row.get("job_id") or ""),
            description=str(row.get("description") or ""),
        )
