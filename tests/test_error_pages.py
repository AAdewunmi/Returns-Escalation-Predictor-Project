# path: tests/test_error_pages.py
"""Tests for custom error handlers and visible guidance."""

from __future__ import annotations

from django.test import RequestFactory

from apps.core.error_views import error_403, error_404, error_500


def test_error_403_returns_forbidden_page() -> None:
    """The forbidden handler should return the branded 403 page."""
    request = RequestFactory().get("/ops/secret/")
    response = error_403(request, Exception("forbidden"))

    assert response.status_code == 403
    assert "You do not have access to this area" in response.content.decode()


def test_error_404_returns_not_found_page() -> None:
    """The not-found handler should return the branded 404 page."""
    request = RequestFactory().get("/missing/")
    response = error_404(request, Exception("not-found"))

    assert response.status_code == 404
    assert "We could not find that page" in response.content.decode()


def test_error_500_returns_server_error_page() -> None:
    """The server-error handler should return the branded 500 page."""
    request = RequestFactory().get("/broken/")
    response = error_500(request)

    assert response.status_code == 500
    assert "Something went wrong on our side" in response.content.decode()
