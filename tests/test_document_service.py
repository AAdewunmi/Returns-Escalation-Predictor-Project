"""Tests for evidence upload service logic."""

from __future__ import annotations

import hashlib

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile

from returns.models import EvidenceDocument
from returns.services.documents import (
    DocumentUploadInput,
    list_documents_for_case,
    upload_document_for_case,
)
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_customer_can_upload_evidence_and_event_is_emitted(monkeypatch) -> None:
    """Customer uploads should persist a document and append a case event."""
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")

    def fake_score_case_and_persist(case, *, triggered_by):
        assert case == return_case
        assert triggered_by == "document_uploaded"
        return None

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        fake_score_case_and_persist,
    )

    uploaded_file = SimpleUploadedFile("photo.jpg", b"customer-photo", content_type="image/jpeg")
    document = upload_document_for_case(
        return_case=return_case,
        actor=customer_user,
        upload_input=DocumentUploadInput(
            kind=EvidenceDocument.DocumentKind.EVIDENCE,
            uploaded_file=uploaded_file,
            notes="Front panel damage",
        ),
    )

    assert document.return_case == return_case
    assert document.uploaded_by == customer_user
    assert document.actor_role == "customer"
    assert document.kind == EvidenceDocument.DocumentKind.EVIDENCE
    assert document.notes == "Front panel damage"
    assert document.visible_to_customer is True
    assert document.visible_to_merchant is False
    assert document.checksum_sha256 == hashlib.sha256(b"customer-photo").hexdigest()
    assert return_case.events.filter(event_type="document_uploaded").count() == 1


@pytest.mark.django_db
def test_customer_cannot_upload_response_document() -> None:
    """Customers should be blocked from uploading merchant response documents."""
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")

    uploaded_file = SimpleUploadedFile(
        "response.pdf",
        b"merchant-response",
        content_type="application/pdf",
    )

    with pytest.raises(PermissionDenied, match="Customers can only upload evidence"):
        upload_document_for_case(
            return_case=return_case,
            actor=customer_user,
            upload_input=DocumentUploadInput(
                kind=EvidenceDocument.DocumentKind.RESPONSE,
                uploaded_file=uploaded_file,
            ),
        )


@pytest.mark.django_db
def test_customer_document_listing_hides_merchant_only_documents() -> None:
    """Customer listings should hide documents not visible to customers."""
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")

    EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        actor_role=EvidenceDocument.ActorRole.MERCHANT,
        kind=EvidenceDocument.DocumentKind.RESPONSE,
        visible_to_customer=False,
        visible_to_merchant=True,
    )

    documents = list_documents_for_case(return_case=return_case, actor=customer_user)

    assert documents.count() == 0


@pytest.mark.django_db
def test_merchant_can_list_documents_visible_to_merchant() -> None:
    """Merchants should only receive documents marked visible to merchants."""
    return_case = ReturnCaseFactory()
    merchant_user = return_case.merchant.user
    add_group(merchant_user, "merchant")

    visible_document = EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        visible_to_customer=True,
        visible_to_merchant=True,
    )
    EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        actor_role=EvidenceDocument.ActorRole.OPS,
        kind=EvidenceDocument.DocumentKind.RESPONSE,
        visible_to_customer=False,
        visible_to_merchant=False,
    )

    documents = list_documents_for_case(return_case=return_case, actor=merchant_user)

    assert list(documents) == [visible_document]
