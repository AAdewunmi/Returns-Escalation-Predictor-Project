# path: tests/test_production_helpers.py
"""Unit tests for production environment parsing helpers."""

from __future__ import annotations

import pytest

from config.settings.production_helpers import env_bool, env_int, env_list


@pytest.mark.parametrize(
    ("raw_value", "default", "expected"),
    [
        (None, False, False),
        (None, True, True),
        ("1", False, True),
        ("true", False, True),
        ("YES", False, True),
        ("on", False, True),
        ("0", True, False),
        ("false", True, False),
    ],
)
def test_env_bool_parses_truthy_falsey_and_default_values(
    monkeypatch, raw_value: str | None, default: bool, expected: bool
) -> None:
    """Boolean helper should support explicit truthy values and fallback defaults."""
    if raw_value is None:
        monkeypatch.delenv("TEST_BOOL", raising=False)
    else:
        monkeypatch.setenv("TEST_BOOL", raw_value)

    assert env_bool("TEST_BOOL", default=default) is expected


def test_env_int_parses_integer_values_and_defaults(monkeypatch) -> None:
    """Integer helper should return defaults when unset and parse numeric strings."""
    monkeypatch.delenv("TEST_INT", raising=False)
    assert env_int("TEST_INT", default=30) == 30

    monkeypatch.setenv("TEST_INT", "120")

    assert env_int("TEST_INT", default=30) == 120


def test_env_list_parses_csv_values_and_defaults(monkeypatch) -> None:
    """Comma-separated values should be trimmed and preserve default behavior."""
    monkeypatch.delenv("TEST_LIST", raising=False)
    assert env_list("TEST_LIST", default=["example.com"]) == ["example.com"]
    assert env_list("TEST_LIST") == []

    monkeypatch.setenv("TEST_LIST", "example.com, api.example.com ,, cdn.example.com ")

    assert env_list("TEST_LIST") == [
        "example.com",
        "api.example.com",
        "cdn.example.com",
    ]
