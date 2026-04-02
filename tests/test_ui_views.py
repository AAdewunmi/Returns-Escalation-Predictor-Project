"""Tests for public UI views and surface entry routes."""

from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from tests.factories import ReturnCaseFactory
from ui.views import BootstrapLandingView, SurfaceEntryView


def test_bootstrap_landing_view_uses_landing_template() -> None:
    """Bootstrap landing view should continue rendering the public landing page."""
    assert BootstrapLandingView.template_name == "public/landing.html"


def test_surface_entry_routes_render_expected_surface_content(client) -> None:
    """Each workspace entry route should render its role-specific surface copy."""
    routes = [
        ("admin-login", b"Admin surface"),
        ("ops-login", b"Ops surface"),
        ("customer-login", b"Customer surface"),
        ("merchant-login", b"Merchant surface"),
    ]

    for route_name, expected_text in routes:
        response = client.get(reverse(route_name))

        assert response.status_code == 200
        assert expected_text in response.content


def test_surface_entry_view_raises_404_for_unknown_surface() -> None:
    """Unknown surface keys should be rejected explicitly."""
    request = RequestFactory().get("/login/unknown/")
    view = SurfaceEntryView()
    view.request = request
    view.kwargs = {"surface": "unknown"}

    try:
        view.get_context_data(surface="unknown")
    except Http404:
        return

    raise AssertionError("Expected SurfaceEntryView to raise Http404 for an unknown surface.")


def test_case_detail_route_renders_project_aligned_case_workspace(client, db) -> None:
    """The case detail route should render the detail template with live case content."""

    return_case = ReturnCaseFactory(order_reference="ORD-DETAIL-001")

    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 200
    assert b"ORD-DETAIL-001" in response.content
    assert b"Return Case Workspace" in response.content
    assert b"Documents" in response.content
    assert b"Timeline" in response.content
