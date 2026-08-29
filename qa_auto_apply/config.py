"""Load JSON configuration from the config/ directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DEFAULT_SETTINGS_PATH = CONFIG_DIR / "settings.json"
DEFAULT_COMPANIES_PATH = CONFIG_DIR / "companies.json"


class ConfigError(RuntimeError):
    """Raised when configuration files are missing or invalid."""


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def load_settings(path: Path | None = None) -> dict[str, Any]:
    data = _read_json(path or DEFAULT_SETTINGS_PATH)
    if not isinstance(data, dict):
        raise ConfigError("settings.json must contain a JSON object")
    return data


def load_companies(path: Path | None = None) -> dict[str, Any]:
    data = _read_json(path or DEFAULT_COMPANIES_PATH)
    if not isinstance(data, dict):
        raise ConfigError("companies.json must contain a JSON object")
    greenhouse = data.get("greenhouse") or []
    lever = data.get("lever") or []
    if not isinstance(greenhouse, list) or not isinstance(lever, list):
        raise ConfigError("companies.json greenhouse/lever values must be arrays")
    return {"greenhouse": greenhouse, "lever": lever}
