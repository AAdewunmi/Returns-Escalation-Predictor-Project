# path: tests/test_public_views.py
"""Smoke tests for public-facing pages."""
import pytest
from django.urls import reverse


def test_landing_page_renders_role_entry_buttons(client) -> None:
    """The landing page should expose all role entry routes."""
    response = client.get(reverse("landing"))

    assert response.status_code == 200
    body = response.content.decode()

    assert "One clear place to triage returns, evidence, and follow-up." in body
    assert reverse("admin-login") in body
    assert reverse("ops-login") in body
    assert reverse("customer-login") in body
    assert reverse("merchant-login") in body

@pytest.mark.parametrize(
    ("route_name", "expected_text"),
    [
        ("admin-login", "Administration entry is reserved and branded."),
        ("ops-login", "Ops entry is reserved for queue-driven work."),
        ("customer-login", "Customer entry is reserved for case tracking."),
        ("merchant-login", "Merchant entry is reserved for linked case responses."),
    ],
)
def test_surface_entry_pages_render_surface_specific_copy(
    client,
    route_name: str,
    expected_text: str,
) -> None:
    """Each public surface entry page should render its own explanatory copy."""
    response = client.get(reverse(route_name))

    assert response.status_code == 200
    assert expected_text in response.content.decode()
