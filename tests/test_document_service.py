# path: tests/test_document_service.py
"""
Tests for evidence upload service logic.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.returns.models import CaseEventType, EvidenceDocumentKind
from apps.returns.services.documents import DocumentUploadInput, list_documents_for_case, upload_document_for_case
from apps.returns.tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_customer_can_upload_evidence_and_event_is_emitted(monkeypatch):
    """
    Customer uploads should persist a document and append a case event.
    """

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)

    monkeypatch.setattr(
        "apps.returns.services.risk.score_case_for_escalation",
        lambda **kwargs: None,
        raising=False,
    )

    uploaded_file = SimpleUploadedFile("photo.jpg", b"customer-photo", content_type="image/jpeg")
    document = upload_document_for_case(
        return_case=return_case,
        actor=customer_user,
        upload_input=DocumentUploadInput(
            document_kind=EvidenceDocumentKind.CUSTOMER_EVIDENCE,
            uploaded_file=uploaded_file,
            note="Front panel damage",
        ),
    )

    assert document.return_case == return_case
    assert return_case.events.filter(event_type=CaseEventType.DOCUMENT_UPLOADED).count() == 1


@pytest.mark.django_db
def test_customer_cannot_see_internal_ops_attachment():
    """
    Customer document listings should hide internal ops attachments.
    """

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)

    EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        uploaded_by_role="ops",
        document_kind=EvidenceDocumentKind.OPS_ATTACHMENT,
        visible_to_customer=False,
        visible_to_merchant=False,
    )

    documents = list_documents_for_case(return_case, customer_user)

    assert documents.count() == 0