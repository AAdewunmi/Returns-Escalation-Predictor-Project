"""Tests for branded error page views."""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from ui.error_views import error_403, error_404, error_500


def _build_request(path: str):
    """Return a request with the minimum context expected by shared processors."""
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    return request


def test_error_403_renders_branded_forbidden_page() -> None:
    """403 handler should render the branded forbidden template with a 403 status."""
    request = _build_request("/forbidden/")

    response = error_403(request, Exception("forbidden"))

    assert response.status_code == 403
    assert b"403 Forbidden" in response.content


def test_error_404_renders_branded_not_found_page() -> None:
    """404 handler should render the branded not found template with a 404 status."""
    request = _build_request("/missing/")

    response = error_404(request, Exception("missing"))

    assert response.status_code == 404
    assert b"404 Not Found" in response.content


def test_error_500_renders_branded_server_error_page() -> None:
    """500 handler should render the branded server error template with a 500 status."""
    request = _build_request("/error/")

    response = error_500(request)

    assert response.status_code == 500
    assert b"500 Server Error" in response.content
