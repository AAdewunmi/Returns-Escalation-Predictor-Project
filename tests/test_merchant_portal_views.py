"""Tests for merchant portal routes and views."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import resolve, reverse
from django.utils import timezone

from returns.models import CaseEvent, EvidenceDocument
from tests.factories import CaseEventFactory, ReturnCaseFactory


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
    older_event = CaseEventFactory(
        return_case=return_case,
        actor=return_case.merchant.user,
        actor_role="merchant",
        event_type="merchant_response_submitted",
        payload={
            "response_note": "Initial warehouse check complete.",
            "document_id": "",
            "document_kind": "",
            "has_document": False,
        },
    )
    latest_event = CaseEventFactory(
        return_case=return_case,
        actor=return_case.merchant.user,
        actor_role="merchant",
        event_type="merchant_response_submitted",
        payload={
            "response_note": "Escalated to carrier with supporting evidence.",
            "document_id": "123",
            "document_kind": "response",
            "has_document": True,
        },
    )
    CaseEvent.objects.filter(pk=older_event.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )
    CaseEvent.objects.filter(pk=latest_event.pk).update(created_at=timezone.now())

    client.force_login(return_case.merchant.user)
    response = client.get(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk})
    )

    assert response.status_code == 200
    assert b"Merchant Case Workspace" in response.content
    assert b"MERCH-DETAIL-001" in response.content
    assert b"Merchant response" in response.content
    assert b"Latest merchant response" in response.content
    assert b"Response history" in response.content
    assert b"Merchant Activity" in response.content
    assert b"Escalated to carrier with supporting evidence." in response.content


def test_merchant_case_detail_post_redirects_after_note_only_submission(
    client,
    db,
    monkeypatch,
) -> None:
    """Valid note-only merchant responses should redirect back to the detail page."""

    return_case = ReturnCaseFactory(order_reference="MERCH-UPLOAD-001")
    add_group(return_case.merchant.user, "merchant")

    captured = {}

    def fake_submit_merchant_response(
        *,
        return_case,
        submitted_by,
        response_note,
        response_file,
    ):
        captured["case"] = return_case
        captured["submitted_by"] = submitted_by
        captured["response_note"] = response_note
        captured["response_file"] = response_file
        return None

    monkeypatch.setattr(
        "returns.views_merchant.submit_merchant_response",
        fake_submit_merchant_response,
    )

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "response_note": "Inspection complete",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "merchant_portal:case_detail",
        kwargs={"case_id": return_case.pk},
    )
    assert captured == {
        "case": return_case,
        "submitted_by": return_case.merchant.user,
        "response_note": "Inspection complete",
        "response_file": None,
    }
    messages = [message.message for message in get_messages(response.wsgi_request)]
    assert "Response submitted successfully." in messages


def test_merchant_can_submit_note_and_file_to_owned_case(client, db, monkeypatch) -> None:
    """Posting a note and file should create both document and merchant response events."""

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
            "response_note": "Response document attached.",
            "response_file": SimpleUploadedFile(
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
    assert (
        CaseEvent.objects.filter(
            return_case=return_case,
            event_type="merchant_response_submitted",
        ).count()
        == 1
    )


def test_merchant_can_submit_note_only_to_owned_case(client, db) -> None:
    """Posting only a note should append a merchant response event without a document."""

    return_case = ReturnCaseFactory(order_reference="MERCH-NOTE-ONLY-001")
    add_group(return_case.merchant.user, "merchant")

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={
            "response_note": "Awaiting carrier confirmation before next step.",
        },
    )

    assert response.status_code == 302
    assert (
        EvidenceDocument.objects.filter(
            return_case=return_case,
            kind=EvidenceDocument.DocumentKind.RESPONSE,
        ).count()
        == 0
    )
    assert (
        CaseEvent.objects.filter(
            return_case=return_case,
            event_type="merchant_response_submitted",
        ).count()
        == 1
    )


def test_merchant_case_detail_post_renders_errors_for_invalid_upload(client, db) -> None:
    """Blank merchant responses should re-render the page with a 400 status."""

    return_case = ReturnCaseFactory(order_reference="MERCH-UPLOAD-002")
    add_group(return_case.merchant.user, "merchant")

    client.force_login(return_case.merchant.user)
    response = client.post(
        reverse("merchant_portal:case_detail", kwargs={"case_id": return_case.pk}),
        data={},
    )

    assert response.status_code == 400
    assert b"Merchant response" in response.content
    assert b"Add a response note, a supporting file, or both." in response.content


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
