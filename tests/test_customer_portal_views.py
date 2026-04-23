"""Tests for customer portal routes and views."""

from __future__ import annotations

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve, reverse

from returns.models import CaseEvent, EvidenceDocument
from tests.factories import ReturnCaseFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def test_customer_portal_routes_resolve_to_live_views() -> None:
    """Customer portal routes should resolve through the project URL config."""

    assert reverse("customer_portal:case_list") == "/customer/"
    assert resolve("/customer/").view_name == "customer_portal:case_list"
    assert (
        reverse(
            "customer_portal:case_detail",
            kwargs={"case_id": 42},
        )
        == "/customer/42/"
    )
    assert resolve("/customer/42/").view_name == "customer_portal:case_detail"


def test_customer_case_list_paginates_and_hides_other_customers(
    client,
    db,
) -> None:
    """Customers should see only their own cases across page 1 and page 2."""

    first_case = ReturnCaseFactory(order_reference="CUST-LIST-001")
    customer_user = first_case.customer.user
    add_group(customer_user, "customer")
    other_case = ReturnCaseFactory(order_reference="CUST-OTHER-001")
    add_group(other_case.customer.user, "customer")

    for index in range(16):
        ReturnCaseFactory(
            customer=first_case.customer,
            merchant=first_case.merchant,
            order_reference=f"CUST-LIST-{index + 2:03d}",
        )

    client.force_login(customer_user)
    response_page_1 = client.get(reverse("customer_portal:case_list"))
    response_page_2 = client.get(f"{reverse('customer_portal:case_list')}?page=2")

    assert response_page_1.status_code == 200
    assert response_page_2.status_code == 200
    assert b"Showing 1-15 of 17" in response_page_1.content
    assert b"Showing 16-17 of 17" in response_page_2.content
    assert b"CUST-OTHER-001" not in response_page_1.content
    assert b"CUST-OTHER-001" not in response_page_2.content


def test_customer_case_list_invalid_and_out_of_range_pages_fall_back_cleanly(
    client,
    db,
) -> None:
    """Invalid pages should resolve to page 1 and out-of-range values to the last page."""

    first_case = ReturnCaseFactory(order_reference="CUST-PAGE-001")
    customer_user = first_case.customer.user
    add_group(customer_user, "customer")

    for index in range(15):
        ReturnCaseFactory(
            customer=first_case.customer,
            merchant=first_case.merchant,
            order_reference=f"CUST-PAGE-{index + 2:03d}",
        )

    client.force_login(customer_user)
    invalid_response = client.get(f"{reverse('customer_portal:case_list')}?page=banana")
    last_page_response = client.get(f"{reverse('customer_portal:case_list')}?page=999")

    assert invalid_response.status_code == 200
    assert last_page_response.status_code == 200
    assert b"Showing 1-15 of 16" in invalid_response.content
    assert b"Showing 16-16 of 16" in last_page_response.content


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
    assert b"Upload evidence" in response.content
    assert b"Uploaded evidence" in response.content
    assert b"No evidence uploaded yet" in response.content


def test_customer_case_detail_post_redirects_after_successful_upload(
    client,
    db,
    monkeypatch,
) -> None:
    """Valid customer uploads should redirect back to the customer case detail page."""

    return_case = ReturnCaseFactory(order_reference="CUST-UPLOAD-001")
    add_group(return_case.customer.user, "customer")

    captured = {}

    def fake_upload_customer_evidence(
        *,
        return_case,
        uploaded_by,
        uploaded_file,
        description,
    ):
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


def test_customer_can_upload_evidence_to_owned_case(client, db, monkeypatch) -> None:
    """Posting an evidence file should create a document and a case event."""

    return_case = ReturnCaseFactory(order_reference="CUST-UPLOAD-REAL-001")
    add_group(return_case.customer.user, "customer")
    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_login(return_case.customer.user)
    response = client.post(
        reverse("customer_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "notes": "Photo of damaged packaging.",
            "file": SimpleUploadedFile(
                "photo.jpg",
                b"binary-image-content",
                content_type="image/jpeg",
            ),
        },
    )

    assert response.status_code == 302
    assert (
        EvidenceDocument.objects.filter(
            return_case=return_case,
            kind=EvidenceDocument.DocumentKind.EVIDENCE,
        ).count()
        == 1
    )
    assert (
        CaseEvent.objects.filter(
            return_case=return_case,
            event_type="document_uploaded",
        ).count()
        == 1
    )


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
    assert b"Upload evidence" in response.content
    assert b"This field is required." in response.content


def test_customer_cannot_open_another_customers_case(client, db) -> None:
    """A customer should receive 404 when trying to open another customer's case."""

    own_case = ReturnCaseFactory(order_reference="CUST-OWN-001")
    other_case = ReturnCaseFactory(order_reference="CUST-OTHER-DETAIL-001")
    add_group(own_case.customer.user, "customer")
    add_group(other_case.customer.user, "customer")

    client.force_login(own_case.customer.user)
    response = client.get(reverse("customer_portal:case_detail", kwargs={"case_id": other_case.pk}))

    assert own_case.customer.pk != other_case.customer.pk
    assert response.status_code == 404
