# path: tests/test_production_helpers.py
"""Unit tests for production environment parsing helpers."""

from __future__ import annotations

from config.settings.production_helpers import env_bool, env_int, env_list


def test_env_bool_parses_truthy_values(monkeypatch) -> None:
    """Truthy string values should evaluate to True."""
    monkeypatch.setenv("TEST_BOOL", "true")

    assert env_bool("TEST_BOOL") is True


def test_env_bool_returns_default_when_missing(monkeypatch) -> None:
    """Missing values should fall back to the provided default."""
    monkeypatch.delenv("TEST_BOOL", raising=False)

    assert env_bool("TEST_BOOL", default=True) is True


def test_env_int_parses_integer_values(monkeypatch) -> None:
    """Integer environment values should be converted safely."""
    monkeypatch.setenv("TEST_INT", "120")

    assert env_int("TEST_INT", default=30) == 120


def test_env_list_parses_csv_values(monkeypatch) -> None:
    """Comma-separated values should be returned as trimmed items."""
    monkeypatch.setenv("TEST_LIST", "example.com, api.example.com ,cdn.example.com")

    assert env_list("TEST_LIST") == [
        "example.com",
        "api.example.com",
        "cdn.example.com",
    ]
