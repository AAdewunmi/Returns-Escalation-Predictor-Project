# path: tests/test_bootstrap.py
"""Smoke tests for the initial project scaffold."""
from django.urls import reverse


def test_bootstrap_landing_page_renders(client) -> None:
    """The root route should render a minimal bootstrap page."""
    response = client.get(reverse("landing"))

    assert response.status_code == 200
    assert b"ReturnHub bootstrap is live." in response.content
