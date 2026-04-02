"""Tests for public UI views and surface entry routes."""

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from returns.models import EvidenceDocument
from tests.factories import ReturnCaseFactory
from ui.views import BootstrapLandingView, SurfaceEntryView


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


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


def test_case_detail_route_renders_upload_form_for_case_customer(client, db) -> None:
    """The case detail page should render an upload form for the linked customer."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-001")
    add_group(return_case.customer.user, "customer")

    client.force_login(return_case.customer.user)
    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 200
    assert b'id="case-upload-form"' in response.content
    assert b"Upload document" in response.content


def test_case_document_upload_returns_updated_panel_and_document_table(
    client,
    db,
    monkeypatch,
) -> None:
    """Uploading from the case detail page should refresh the local fragments only."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-002")
    add_group(return_case.customer.user, "customer")
    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        data={
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "notes": "Front damage photo",
            "file": SimpleUploadedFile("photo.jpg", b"img-bytes", content_type="image/jpeg"),
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Document uploaded successfully." in payload["upload_panel_html"]
    assert "photo.jpg" in payload["document_table_html"]
    assert return_case.documents.count() == 1
