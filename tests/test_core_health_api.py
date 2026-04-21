"""Tests for core health helpers and readiness API views."""

from __future__ import annotations

from datetime import UTC, datetime

from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.test import APIRequestFactory

from core.api.views import HealthCheckView
from core.health import check_database, get_readiness_payload


class _HealthyCursor:
    """Minimal cursor stub for the successful database probe path."""

    def __init__(self) -> None:
        self.executed_sql: list[str] = []
        self.fetchone_calls = 0

    def __enter__(self) -> _HealthyCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)

    def fetchone(self) -> tuple[int]:
        self.fetchone_calls += 1
        return (1,)


class _HealthyConnection:
    """Connection stub that returns the supplied cursor."""

    def __init__(self, cursor: _HealthyCursor) -> None:
        self._cursor = cursor

    def cursor(self) -> _HealthyCursor:
        return self._cursor


class _UnavailableConnection:
    """Connection stub that raises the expected operational error."""

    def cursor(self):
        raise OperationalError("database unavailable")


def test_check_database_returns_ok_when_default_database_is_reachable(monkeypatch) -> None:
    """The probe should execute a lightweight query and report success."""

    cursor = _HealthyCursor()
    monkeypatch.setattr(
        "core.health.connections",
        {"default": _HealthyConnection(cursor)},
    )

    assert check_database() == (True, "ok")
    assert cursor.executed_sql == ["SELECT 1"]
    assert cursor.fetchone_calls == 1


def test_check_database_returns_unavailable_on_operational_error(monkeypatch) -> None:
    """Operational errors should degrade the readiness dependency check."""

    monkeypatch.setattr(
        "core.health.connections",
        {"default": _UnavailableConnection()},
    )

    assert check_database() == (False, "unavailable")


def test_get_readiness_payload_includes_release_timestamp_and_checks(monkeypatch, settings) -> None:
    """The readiness payload should expose the stable response contract."""

    fixed_now = datetime(2026, 4, 21, 9, 3, 36, tzinfo=UTC)
    monkeypatch.setattr("core.health.check_database", lambda: (True, "ok"))
    monkeypatch.setattr("core.health.timezone.now", lambda: fixed_now)
    settings.RELEASE_VERSION = "2026.04.21"

    assert get_readiness_payload() == {
        "status": "ok",
        "service": "returnhub",
        "release": "2026.04.21",
        "timestamp": fixed_now.isoformat(),
        "checks": {"database": "ok"},
    }


def test_get_readiness_payload_falls_back_to_degraded_and_dev_release(
    monkeypatch, settings
) -> None:
    """The helper should preserve safe defaults for degraded environments."""

    fixed_now = datetime(2026, 4, 21, 9, 3, 36, tzinfo=UTC)
    monkeypatch.setattr("core.health.check_database", lambda: (False, "unavailable"))
    monkeypatch.setattr("core.health.timezone.now", lambda: fixed_now)
    del settings.RELEASE_VERSION

    assert get_readiness_payload() == {
        "status": "degraded",
        "service": "returnhub",
        "release": "dev",
        "timestamp": fixed_now.isoformat(),
        "checks": {"database": "unavailable"},
    }


def test_health_check_view_returns_200_for_healthy_payload(monkeypatch) -> None:
    """The API view should return 200 when the app is ready."""

    monkeypatch.setattr(
        "core.api.views.get_readiness_payload",
        lambda: {"status": "ok", "checks": {"database": "ok"}},
    )

    response = HealthCheckView.as_view()(APIRequestFactory().get("/api/health/"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"status": "ok", "checks": {"database": "ok"}}


def test_health_check_view_returns_503_for_degraded_payload(monkeypatch) -> None:
    """The API view should signal unready status to probes and load balancers."""

    monkeypatch.setattr(
        "core.api.views.get_readiness_payload",
        lambda: {"status": "degraded", "checks": {"database": "unavailable"}},
    )

    response = HealthCheckView.as_view()(APIRequestFactory().get("/api/health/"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data == {"status": "degraded", "checks": {"database": "unavailable"}}
