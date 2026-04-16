"""Tests for merchant portal routes and views."""

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


def test_merchant_portal_routes_resolve_to_live_views() -> None:
    """Merchant portal routes should resolve through the project URL config."""

    assert reverse("merchant_portal:case_list") == "/merchant/"
    assert resolve("/merchant/").view_name == "merchant_portal:case_list"
    assert (
        reverse(
            "merchant_portal:case_detail",
            kwargs={"case_id": 42},
        )
        == "/merchant/42/"
    )
    assert resolve("/merchant/42/").view_name == "merchant_portal:case_detail"


def test_merchant_case_list_paginates_and_hides_other_merchants(
    client,
    db,
) -> None:
    """Merchants should see only their own cases across page 1 and page 2."""

    first_case = ReturnCaseFactory(order_reference="MERCH-LIST-001")
    merchant_user = first_case.merchant.user
    add_group(merchant_user, "merchant")
    other_case = ReturnCaseFactory(order_reference="MERCH-OTHER-001")
    add_group(other_case.merchant.user, "merchant")

    for index in range(16):
        ReturnCaseFactory(
            customer=first_case.customer,
            merchant=first_case.merchant,
            order_reference=f"MERCH-LIST-{index + 2:03d}",
        )

    client.force_login(merchant_user)
    response_page_1 = client.get(reverse("merchant_portal:case_list"))
    response_page_2 = client.get(f"{reverse('merchant_portal:case_list')}?page=2")

    assert response_page_1.status_code == 200
    assert response_page_2.status_code == 200
    assert b"Showing 1-15 of 17" in response_page_1.content
    assert b"Showing 16-17 of 17" in response_page_2.content
    assert b"MERCH-OTHER-001" not in response_page_1.content
    assert b"MERCH-OTHER-001" not in response_page_2.content


def test_merchant_case_list_invalid_and_out_of_range_pages_fall_back_cleanly(
    client,
    db,
) -> None:
    """Invalid pages should resolve to page 1 and out-of-range values to the last page."""

    first_case = ReturnCaseFactory(order_reference="MERCH-PAGE-001")
    merchant_user = first_case.merchant.user
    add_group(merchant_user, "merchant")

    for index in range(15):
        ReturnCaseFactory(
            customer=first_case.customer,
            merchant=first_case.merchant,
            order_reference=f"MERCH-PAGE-{index + 2:03d}",
        )

    client.force_login(merchant_user)
    invalid_response = client.get(f"{reverse('merchant_portal:case_list')}?page=banana")
    last_page_response = client.get(f"{reverse('merchant_portal:case_list')}?page=999")

    assert invalid_response.status_code == 200
    assert last_page_response.status_code == 200
    assert b"Showing 1-15 of 16" in invalid_response.content
    assert b"Showing 16-16 of 16" in last_page_response.content


def test_merchant_case_detail_view_renders_for_linked_merchant(client, db) -> None:
    """The merchant portal detail page should render the linked case workspace."""

    return_case = ReturnCaseFactory(order_reference="MERCH-DETAIL-001")
    add_group(return_case.merchant.user, "merchant")

    client.force_login(return_case.merchant.user)
    response = client.get(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk})
    )

    assert response.status_code == 200
    assert b"Merchant Case Workspace" in response.content
    assert b"MERCH-DETAIL-001" in response.content
    assert b"Merchant response" in response.content


def test_merchant_case_detail_post_redirects_after_successful_upload(
    client,
    db,
    monkeypatch,
) -> None:
    """Valid merchant uploads should redirect back to the merchant case detail page."""

    return_case = ReturnCaseFactory(order_reference="MERCH-UPLOAD-001")
    add_group(return_case.merchant.user, "merchant")

    captured = {}

    def fake_upload_merchant_response(
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
        "returns.views_merchant.upload_merchant_response",
        fake_upload_merchant_response,
    )

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "kind": "response",
            "notes": "Inspection complete",
            "file": SimpleUploadedFile("response.jpg", b"jpg", content_type="image/jpeg"),
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "merchant_portal:case_detail",
        kwargs={"case_id": return_case.pk},
    )
    assert captured == {
        "case": return_case,
        "uploaded_by": return_case.merchant.user,
        "filename": "response.jpg",
        "description": "Inspection complete",
    }
    messages = [message.message for message in get_messages(response.wsgi_request)]
    assert "Response uploaded successfully." in messages


def test_merchant_can_upload_response_to_owned_case(client, db, monkeypatch) -> None:
    """Posting a response file should create a document and a case event."""

    return_case = ReturnCaseFactory(order_reference="MERCH-UPLOAD-REAL-001")
    add_group(return_case.merchant.user, "merchant")
    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "kind": EvidenceDocument.DocumentKind.RESPONSE,
            "notes": "Response document attached.",
            "file": SimpleUploadedFile(
                "response.jpg",
                b"binary-image-content",
                content_type="image/jpeg",
            ),
        },
    )

    assert response.status_code == 302
    assert (
        EvidenceDocument.objects.filter(
            return_case=return_case,
            kind=EvidenceDocument.DocumentKind.RESPONSE,
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


def test_merchant_case_detail_post_renders_errors_for_invalid_upload(client, db) -> None:
    """Invalid merchant uploads should re-render the page with a 400 status."""

    return_case = ReturnCaseFactory(order_reference="MERCH-UPLOAD-002")
    add_group(return_case.merchant.user, "merchant")

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={"kind": "response", "notes": "Missing file"},
    )

    assert response.status_code == 400
    assert b"Merchant response" in response.content
    assert b"This field is required." in response.content


def test_merchant_cannot_open_another_merchants_case(client, db) -> None:
    """A merchant should receive 404 when trying to open another merchant's case."""

    own_case = ReturnCaseFactory(order_reference="MERCH-OWN-001")
    other_case = ReturnCaseFactory(order_reference="MERCH-OTHER-DETAIL-001")
    add_group(own_case.merchant.user, "merchant")
    add_group(other_case.merchant.user, "merchant")

    client.force_login(own_case.merchant.user)
    response = client.get(reverse("merchant_portal:case_detail", kwargs={"case_id": other_case.pk}))

    assert own_case.merchant.pk != other_case.merchant.pk
    assert response.status_code == 404
