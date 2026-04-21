"""Integration tests for the readiness endpoint."""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_returns_ok_when_database_is_available(client) -> None:
    """The readiness endpoint should return a 200 response when checks pass."""
    response = client.get(reverse("core_api:health"))

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "returnhub"
    assert payload["checks"]["database"] == "ok"
    assert "timestamp" in payload


def test_health_endpoint_returns_503_when_required_check_fails(client, monkeypatch) -> None:
    """A degraded dependency should produce a 503 response and stable payload shape."""
    monkeypatch.setattr(
        "core.api.views.get_readiness_payload",
        lambda: {
            "status": "degraded",
            "service": "returnhub",
            "release": "test",
            "timestamp": "2026-03-09T09:00:00+00:00",
            "checks": {"database": "unavailable"},
        },
    )

    response = client.get(reverse("core_api:health"))

    assert response.status_code == 503
    payload = response.json()

    assert payload["status"] == "degraded"
    assert payload["checks"]["database"] == "unavailable"
