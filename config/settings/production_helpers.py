# path: config/settings/production_helpers.py
"""Helpers for parsing environment-driven production settings."""

from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    """Return an environment variable parsed as a boolean."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    """Return an environment variable parsed as an integer."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value.strip())


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Return a comma-separated environment variable parsed into a list."""
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default or []

    return [item.strip() for item in raw_value.split(",") if item.strip()]
