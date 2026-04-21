# path: tests/test_security_headers.py
"""Integration tests for visible security headers."""

from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
@override_settings(
    DEBUG=False,
    SECURE_REFERRER_POLICY="same-origin",
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    X_FRAME_OPTIONS="DENY",
)
def test_landing_page_includes_expected_security_headers(client) -> None:
    """A real HTML page should emit the expected security headers."""
    response = client.get(reverse("landing"))

    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
