"""Tests for customer portal routes and views."""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve, reverse

from tests.factories import ReturnCaseFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def test_customer_portal_routes_resolve_to_live_views() -> None:
    """Customer portal routes should resolve through the project URL config."""

    assert reverse("customer_portal:case_list") == "/customer/"
    assert resolve("/customer/").view_name == "customer_portal:case_list"
    assert reverse("customer_portal:case_detail", kwargs={"case_id": 42}) == "/customer/42/"
    assert resolve("/customer/42/").view_name == "customer_portal:case_detail"


def test_customer_case_list_view_renders_for_linked_customer(client, db) -> None:
    """The customer portal list should render the current customer's cases."""

    return_case = ReturnCaseFactory(order_reference="CUST-LIST-001")
    add_group(return_case.customer.user, "customer")

    client.force_login(return_case.customer.user)
    response = client.get(reverse("customer_portal:case_list"))

    assert response.status_code == 200
    assert b"Customer Portal" in response.content
    assert b"CUST-LIST-001" in response.content


def test_customer_case_detail_view_renders_for_linked_customer(client, db) -> None:
    """The customer portal detail page should render the linked case workspace."""

    return_case = ReturnCaseFactory(order_reference="CUST-DETAIL-001")
    add_group(return_case.customer.user, "customer")

    client.force_login(return_case.customer.user)
    response = client.get(
        reverse("customer_portal:case_detail", kwargs={"case_id": return_case.pk})
    )

    assert response.status_code == 200
    assert b"Customer Case Workspace" in response.content
    assert b"CUST-DETAIL-001" in response.content
    assert b"Document actions" in response.content


def test_customer_case_detail_post_redirects_after_successful_upload(
    client,
    db,
    monkeypatch,
) -> None:
    """Valid customer uploads should redirect back to the customer case detail page."""

    return_case = ReturnCaseFactory(order_reference="CUST-UPLOAD-001")
    add_group(return_case.customer.user, "customer")

    captured = {}

    def fake_upload_customer_evidence(*, return_case, uploaded_by, uploaded_file, description):
        captured["case"] = return_case
        captured["uploaded_by"] = uploaded_by
        captured["filename"] = uploaded_file.name
        captured["description"] = description
        return None

    monkeypatch.setattr(
        "returns.views_customer.upload_customer_evidence",
        fake_upload_customer_evidence,
    )

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("customer_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "kind": "evidence",
            "notes": "Front panel damage",
            "file": SimpleUploadedFile("photo.jpg", b"jpg", content_type="image/jpeg"),
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "customer_portal:case_detail",
        kwargs={"case_id": return_case.pk},
    )
    assert captured == {
        "case": return_case,
        "uploaded_by": return_case.customer.user,
        "filename": "photo.jpg",
        "description": "Front panel damage",
    }
    messages = [message.message for message in get_messages(response.wsgi_request)]
    assert "Document uploaded successfully." in messages


def test_customer_case_detail_post_renders_errors_for_invalid_upload(client, db) -> None:
    """Invalid customer uploads should re-render the page with a 400 status."""

    return_case = ReturnCaseFactory(order_reference="CUST-UPLOAD-002")
    add_group(return_case.customer.user, "customer")

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("customer_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={"kind": "evidence", "notes": "Missing file"},
    )

    assert response.status_code == 400
    assert b"Document actions" in response.content
    assert b"This field is required." in response.content
