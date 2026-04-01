# path: tests/test_return_documents_api.py
"""
API tests for case document endpoints.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.returns.models import EvidenceDocumentKind
from apps.returns.tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_customer_can_upload_document_via_api():
    """
    Authenticated customers should be able to upload evidence for their own case.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)
    client.force_authenticate(user=customer_user)

    response = client.post(
        f"/api/returns/{return_case.id}/documents/",
        {
            "document_kind": EvidenceDocumentKind.CUSTOMER_EVIDENCE,
            "file": SimpleUploadedFile("photo.jpg", b"abc", content_type="image/jpeg"),
            "note": "Visible scratch on screen",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["document_kind"] == EvidenceDocumentKind.CUSTOMER_EVIDENCE
    assert response.data["uploaded_by_role"] == "customer"


@pytest.mark.django_db
def test_wrong_customer_gets_forbidden_for_other_case():
    """
    A customer must not upload documents against another customer's case.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()
    other_user = UserFactory()
    Group.objects.get_or_create(name="customer")[0].user_set.add(other_user)
    client.force_authenticate(user=other_user)

    response = client.post(
        f"/api/returns/{return_case.id}/documents/",
        {
            "document_kind": EvidenceDocumentKind.CUSTOMER_EVIDENCE,
            "file": SimpleUploadedFile("photo.jpg", b"abc", content_type="image/jpeg"),
        },
        format="multipart",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_listing_hides_internal_ops_documents():
    """
    GET document list should filter visibility by actor role.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)
    client.force_authenticate(user=customer_user)

    EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by_role="ops",
        document_kind=EvidenceDocumentKind.OPS_ATTACHMENT,
        visible_to_customer=False,
        visible_to_merchant=False,
    )

    response = client.get(f"/api/returns/{return_case.id}/documents/")

    assert response.status_code == 200
    assert response.data == []
