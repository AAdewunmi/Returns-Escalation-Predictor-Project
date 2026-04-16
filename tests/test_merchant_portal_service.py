"""Tests for merchant-portal service helpers."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

from returns.models import EvidenceDocument
from returns.services.merchant_portal import (
    build_merchant_case_page,
    get_merchant_case_for_user,
    submit_merchant_response,
)
from tests.factories import (
    CaseEventFactory,
    EvidenceDocumentFactory,
    ReturnCaseFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_build_merchant_case_page_returns_only_merchant_cases_and_pagination() -> None:
    """Merchant pages should scope cases to the signed-in merchant and preserve filters."""

    owned_case = ReturnCaseFactory(status="waiting_merchant")
    other_case = ReturnCaseFactory(status="waiting_merchant")
    merchant_user = owned_case.merchant.user
    add_group(merchant_user, "merchant")

    context = build_merchant_case_page(
        merchant_user,
        QueryDict("status=waiting_merchant&page=2"),
    )

    assert list(context["cases"]) == [owned_case]
    assert context["page_obj"].number == 1
    assert context["pagination"].count_line == "Showing 1-1 of 1"
    assert context["selected_status"] == "waiting_merchant"
    assert context["query_string"] == "status=waiting_merchant"
    assert other_case not in context["cases"]


@pytest.mark.django_db
def test_get_merchant_case_for_user_filters_customer_only_documents() -> None:
    """Merchant detail should exclude customer-only documents from the prefetched relation."""

    return_case = ReturnCaseFactory()
    merchant_user = return_case.merchant.user
    add_group(merchant_user, "merchant")
    visible_document = EvidenceDocumentFactory(
        return_case=return_case,
        visible_to_customer=False,
        visible_to_merchant=True,
    )
    EvidenceDocumentFactory(
        return_case=return_case,
        visible_to_customer=True,
        visible_to_merchant=False,
    )
    CaseEventFactory(return_case=return_case, actor=merchant_user)

    fetched_case = get_merchant_case_for_user(merchant_user, return_case.pk)

    assert list(fetched_case.documents.all()) == [visible_document]


@pytest.mark.django_db
def test_submit_merchant_response_allows_note_only_event_capture() -> None:
    """Note-only merchant responses should append an event without creating a document."""

    return_case = ReturnCaseFactory()
    merchant_user = return_case.merchant.user
    add_group(merchant_user, "merchant")

    document = submit_merchant_response(
        return_case,
        merchant_user,
        response_note="Warehouse inspection completed.",
    )

    event = return_case.events.get(event_type="merchant_response_submitted")

    assert document is None
    assert event.actor == merchant_user
    assert event.actor_role == EvidenceDocument.ActorRole.MERCHANT
    assert event.payload["response_note"] == "Warehouse inspection completed."
    assert event.payload["has_document"] is False


@pytest.mark.django_db
def test_submit_merchant_response_uses_canonical_document_service(monkeypatch) -> None:
    """Merchant file responses should delegate document persistence to the shared workflow."""

    return_case = ReturnCaseFactory()
    merchant_user = return_case.merchant.user
    add_group(merchant_user, "merchant")
    uploaded_file = SimpleUploadedFile("response.jpg", b"jpg", content_type="image/jpeg")

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    document = submit_merchant_response(
        return_case,
        merchant_user,
        response_note="Inspection notes attached",
        response_file=uploaded_file,
    )

    event = return_case.events.get(event_type="merchant_response_submitted")

    assert document.kind == EvidenceDocument.DocumentKind.RESPONSE
    assert document.actor_role == EvidenceDocument.ActorRole.MERCHANT
    assert document.notes == "Inspection notes attached"
    assert document.visible_to_customer is False
    assert document.visible_to_merchant is True
    assert return_case.events.filter(event_type="document_uploaded").count() == 1
    assert event.payload["response_note"] == "Inspection notes attached"
    assert event.payload["document_id"] == str(document.pk)
    assert event.payload["has_document"] is True


@pytest.mark.django_db
def test_admin_can_access_any_merchant_case() -> None:
    """Admin users should be able to fetch any merchant case."""

    return_case = ReturnCaseFactory()
    admin_user = UserFactory(is_superuser=True, is_staff=True)

    fetched_case = get_merchant_case_for_user(admin_user, return_case.pk)

    assert fetched_case == return_case
