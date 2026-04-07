"""Tests for public UI views and surface entry routes."""

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory
from django.urls import reverse

from returns.models import EvidenceDocument
from tests.factories import ReturnCaseFactory, UserFactory
from ui.forms import CaseDocumentUploadForm
from ui.views import (
    BootstrapLandingView,
    ReturnCaseDetailView,
    ReturnCaseDocumentUploadView,
    SurfaceEntryView,
)


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


def test_case_document_upload_form_limits_customer_choices() -> None:
    """Customer upload forms should only offer the evidence document kind."""

    form = CaseDocumentUploadForm(actor_role="customer")

    assert form.fields["kind"].choices == [
        (
            EvidenceDocument.DocumentKind.EVIDENCE,
            EvidenceDocument.DocumentKind.EVIDENCE.label,
        )
    ]


def test_case_document_upload_form_limits_merchant_choices() -> None:
    """Merchant upload forms should only offer the response document kind."""

    form = CaseDocumentUploadForm(actor_role="merchant")

    assert form.fields["kind"].choices == [
        (
            EvidenceDocument.DocumentKind.RESPONSE,
            EvidenceDocument.DocumentKind.RESPONSE.label,
        )
    ]


def test_case_document_upload_form_allows_ops_choices() -> None:
    """Ops users should retain both document-kind choices."""

    form = CaseDocumentUploadForm(actor_role="ops")

    assert list(form.fields["kind"].choices) == list(EvidenceDocument.DocumentKind.choices)


def test_case_document_upload_form_blocks_unknown_role_choices() -> None:
    """Unknown actors should not be offered any upload kind choices."""

    form = CaseDocumentUploadForm(actor_role="")

    assert form.fields["kind"].choices == []


def test_case_document_upload_form_rejects_wrong_customer_kind() -> None:
    """Customer-bound forms should reject response uploads during validation."""

    form = CaseDocumentUploadForm(
        data={"kind": EvidenceDocument.DocumentKind.RESPONSE, "notes": ""},
        files={
            "file": SimpleUploadedFile(
                "response.pdf",
                b"response",
                content_type="application/pdf",
            )
        },
        actor_role="customer",
    )

    assert form.is_valid() is False
    assert "Select a valid choice." in form.errors["kind"][0]


def test_case_detail_view_hides_form_for_unlinked_authenticated_user(db) -> None:
    """Authenticated users outside the case should not receive an upload form."""

    return_case = ReturnCaseFactory()
    request = RequestFactory().get(f"/cases/{return_case.pk}/")
    request.user = UserFactory()
    view = ReturnCaseDetailView()
    view.setup(request, case_id=return_case.pk)

    context = view.get_context_data(case_id=return_case.pk)

    assert context["actor_role"] == ""
    assert context["upload_form"] is None


def test_case_detail_view_returns_no_documents_when_listing_is_forbidden(db, monkeypatch) -> None:
    """Case detail should degrade to an empty document list on permission failure."""

    return_case = ReturnCaseFactory()
    request = RequestFactory().get(f"/cases/{return_case.pk}/")
    request.user = return_case.customer.user
    add_group(request.user, "customer")
    view = ReturnCaseDetailView()
    view.setup(request, case_id=return_case.pk)
    monkeypatch.setattr(
        "returns.services.ops_case_detail.list_documents_for_case",
        lambda **kwargs: (_ for _ in ()).throw(PermissionDenied("forbidden")),
    )

    context = view.get_context_data(case_id=return_case.pk)

    assert list(context["documents"]) == []


def test_case_document_upload_returns_403_for_unlinked_user(client, db) -> None:
    """Users outside the case should receive a local unauthorized upload response."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-003")
    outsider = UserFactory()
    add_group(outsider, "customer")

    client.force_login(outsider)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        data={},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403
    payload = response.json()
    assert "Actor role unavailable" in payload["upload_panel_html"]


def test_case_document_upload_returns_form_errors_for_invalid_submission(client, db) -> None:
    """Invalid uploads should stay local to the upload panel."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-004")
    add_group(return_case.customer.user, "customer")

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        data={"kind": EvidenceDocument.DocumentKind.EVIDENCE, "notes": ""},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    payload = response.json()
    assert "There is a problem with this upload" in payload["upload_panel_html"]


def test_case_document_upload_returns_service_errors_in_panel(client, db, monkeypatch) -> None:
    """Business-rule upload errors should render back into the local panel."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-005")
    add_group(return_case.customer.user, "customer")

    def fail_upload(**kwargs):
        raise PermissionDenied("Customers can only upload evidence to their own cases.")

    monkeypatch.setattr("ui.views.upload_document_for_case", fail_upload)

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        data={
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "notes": "Bad upload",
            "file": SimpleUploadedFile("photo.jpg", b"img-bytes", content_type="image/jpeg"),
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403
    payload = response.json()
    assert "Customers can only upload evidence to their own cases." in payload["upload_panel_html"]


def test_case_document_upload_view_returns_empty_documents_on_render_permission_failure(
    db,
    monkeypatch,
) -> None:
    """Fragment rendering should fall back to an empty document table when listing fails."""

    return_case = ReturnCaseFactory(order_reference="ORD-UP-006")
    request = RequestFactory().post(f"/cases/{return_case.pk}/documents/upload/")
    request.user = return_case.customer.user
    add_group(request.user, "customer")
    view = ReturnCaseDocumentUploadView()
    view.setup(request, case_id=return_case.pk)
    monkeypatch.setattr(
        "ui.views.list_documents_for_case",
        lambda **kwargs: (_ for _ in ()).throw(PermissionDenied("forbidden")),
    )

    response = view._render_response(
        return_case=return_case,
        upload_form=CaseDocumentUploadForm(actor_role="customer"),
        actor_role="customer",
    )

    assert response.status_code == 200
    assert "No documents yet" in response.content.decode()
