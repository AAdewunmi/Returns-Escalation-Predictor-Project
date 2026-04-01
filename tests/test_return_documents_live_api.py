# path: tests/test_return_documents_live_api.py
"""
DB-backed regression tests for the canonical live return-documents route.
"""

from __future__ import annotations

import hashlib

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.returns.models import CaseEvent, EvidenceDocument
from apps.returns.tests.factories import ReturnCaseFactory, UserFactory


def _ensure_group(name: str) -> Group:
    """
    Create the group if missing and return it.
    """

    group, _ = Group.objects.get_or_create(name=name)
    return group


@pytest.mark.django_db
def test_live_get_returns_200_for_case_customer_and_omits_internal_ops_attachments():
    """
    The owning customer should receive HTTP 200 and should not see internal ops-only documents.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")
    ops_group = _ensure_group("ops")

    customer_user = return_case.customer_profile.user
    customer_group.user_set.add(customer_user)

    ops_user = UserFactory(username="ops-live-docs")
    ops_group.user_set.add(ops_user)

    # Visible customer document.
    visible_file = SimpleUploadedFile("seed-photo.jpg", b"seed-bytes", content_type="image/jpeg")
    EvidenceDocument.objects.create(
        return_case=return_case,
        uploaded_by=customer_user,
        actor_role="customer",
        kind="evidence",
        file=visible_file,
        file_path=f"return-cases/{return_case.id}/evidence/2026/04/seed-photo.jpg",
        original_filename="seed-photo.jpg",
        content_type="image/jpeg",
        byte_size=visible_file.size,
        checksum_sha256=hashlib.sha256(b"seed-bytes").hexdigest(),
        notes="Seed document",
        visible_to_customer=True,
        visible_to_merchant=True,
    )

    # Internal ops attachment hidden from customer.
    internal_file = SimpleUploadedFile("ops-internal.txt", b"internal", content_type="text/plain")
    EvidenceDocument.objects.create(
        return_case=return_case,
        uploaded_by=ops_user,
        actor_role="ops",
        kind="evidence",
        file=internal_file,
        file_path=f"return-cases/{return_case.id}/evidence/2026/04/ops-internal.txt",
        original_filename="ops-internal.txt",
        content_type="text/plain",
        byte_size=internal_file.size,
        checksum_sha256=hashlib.sha256(b"internal").hexdigest(),
        notes="Internal ops attachment",
        visible_to_customer=False,
        visible_to_merchant=False,
    )

    client.force_authenticate(user=customer_user)
    response = client.get(f"/api/returns/{return_case.id}/documents/")

    assert response.status_code == 200
    returned_filenames = [item["original_filename"] for item in response.data]
    assert "seed-photo.jpg" in returned_filenames
    assert "ops-internal.txt" not in returned_filenames


@pytest.mark.django_db
def test_live_post_returns_201_with_metadata_and_creates_document_uploaded_event():
    """
    The owning customer should be able to upload a JPG and receive a metadata-rich response.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")
    customer_user = return_case.customer_profile.user
    customer_group.user_set.add(customer_user)

    client.force_authenticate(user=customer_user)
    response = client.post(
        f"/api/returns/{return_case.id}/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Visible damage",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["kind"] == "evidence"
    assert response.data["original_filename"] == "photo.jpg"
    assert response.data["content_type"] == "image/jpeg"
    assert response.data["byte_size"] == 5
    assert response.data["notes"] == "Visible damage"
    assert response.data["actor_role"] == "customer"
    assert response.data["visible_to_customer"] is True
    assert response.data["visible_to_merchant"] is False
    assert response.data["file_path"].startswith(f"return-cases/{return_case.id}/evidence/")

    assert CaseEvent.objects.filter(
        return_case=return_case,
        event_type="document_uploaded",
    ).exists()


@pytest.mark.django_db
def test_live_post_returns_403_for_wrong_customer():
    """
    A different customer must not be allowed to upload against another customer's case.
    """

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")

    wrong_customer = UserFactory(username="wrong-customer-live-docs")
    customer_group.user_set.add(wrong_customer)

    client.force_authenticate(user=wrong_customer)
    response = client.post(
        f"/api/returns/{return_case.id}/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Should be forbidden",
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert response.data["detail"] == "You do not have permission to upload this document for the case."
