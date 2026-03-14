"""Tests for branded error handling."""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, override_settings

from ui.error_views import error_403, error_404, error_500


def _build_request(path: str):
    """Return a request with the minimum context expected by shared processors."""
    request = RequestFactory().get(path)
    request.user = AnonymousUser()
    return request


def test_error_403_view_renders_branded_template() -> None:
    """The custom 403 view should render a branded forbidden page."""
    request = _build_request("/forbidden/")
    response = error_403(request, PermissionDenied("forbidden"))

    assert response.status_code == 403
    assert b"403 Forbidden" in response.content


def test_error_404_renders_branded_not_found_page() -> None:
    """The custom 404 view should render a branded not found page."""
    request = _build_request("/missing/")
    response = error_404(request, Exception("missing"))

    assert response.status_code == 404
    assert b"404 Not Found" in response.content


def test_error_500_view_renders_branded_template() -> None:
    """The custom 500 view should render a branded server error page."""
    request = _build_request("/error/")
    response = error_500(request)

    assert response.status_code == 500
    assert b"500 Server Error" in response.content


@override_settings(DEBUG=False)
def test_missing_route_uses_custom_404_template(client) -> None:
    """Unknown routes should render the branded 404 page when debug is disabled."""
    response = client.get("/missing-route/")

    assert response.status_code == 404
    assert b"404 Not Found" in response.content
