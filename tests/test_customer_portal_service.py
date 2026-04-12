"""Tests for customer-portal service helpers."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict

from returns.models import EvidenceDocument
from returns.services.customer_portal import (
    build_customer_case_page,
    get_customer_case_for_user,
    upload_customer_evidence,
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
def test_build_customer_case_page_returns_only_customer_cases_and_pagination() -> None:
    """Customer pages should scope cases to the signed-in customer and preserve filters."""

    owned_case = ReturnCaseFactory(status="submitted")
    other_case = ReturnCaseFactory(status="submitted")
    customer_user = owned_case.customer.user
    add_group(customer_user, "customer")

    context = build_customer_case_page(
        customer_user,
        QueryDict("status=submitted&page=2"),
    )

    assert list(context["cases"]) == [owned_case]
    assert context["page_obj"].number == 1
    assert context["pagination"].count_line == "Showing 1-1 of 1"
    assert context["selected_status"] == "submitted"
    assert context["query_string"] == "status=submitted"
    assert other_case not in context["cases"]


@pytest.mark.django_db
def test_get_customer_case_for_user_filters_hidden_documents() -> None:
    """Customer detail should exclude merchant-only documents from the prefetched relation."""

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")
    visible_document = EvidenceDocumentFactory(
        return_case=return_case,
        visible_to_customer=True,
    )
    EvidenceDocumentFactory(
        return_case=return_case,
        visible_to_customer=False,
        visible_to_merchant=True,
    )
    CaseEventFactory(return_case=return_case, actor=customer_user)

    fetched_case = get_customer_case_for_user(customer_user, return_case.pk)

    assert list(fetched_case.documents.all()) == [visible_document]


@pytest.mark.django_db
def test_upload_customer_evidence_uses_canonical_document_service(monkeypatch) -> None:
    """Customer evidence uploads should delegate to the shared document workflow."""

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")
    uploaded_file = SimpleUploadedFile("photo.jpg", b"jpg", content_type="image/jpeg")

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    document = upload_customer_evidence(
        return_case,
        customer_user,
        uploaded_file,
        description="Front panel damage",
    )

    assert document.kind == EvidenceDocument.DocumentKind.EVIDENCE
    assert document.actor_role == EvidenceDocument.ActorRole.CUSTOMER
    assert document.notes == "Front panel damage"
    assert document.visible_to_customer is True
    assert document.visible_to_merchant is False
    assert return_case.events.filter(event_type="document_uploaded").count() == 1


@pytest.mark.django_db
def test_admin_can_access_any_customer_case() -> None:
    """Admin users should be able to fetch any customer case."""

    return_case = ReturnCaseFactory()
    admin_user = UserFactory(is_superuser=True, is_staff=True)

    fetched_case = get_customer_case_for_user(admin_user, return_case.pk)

    assert fetched_case == return_case
