"""Tests for the live returns documents API route."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from returns.models import EvidenceDocument
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


def _ensure_group(name: str) -> Group:
    """Create the group if missing and return it."""

    group, _ = Group.objects.get_or_create(name=name)
    return group


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
def test_live_returns_documents_get_endpoint_lists_customer_visible_documents() -> None:
    """The main returns API should expose customer-visible documents."""
    client = APIClient()
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    _ensure_group("customer").user_set.add(customer_user)

    visible_document = EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=customer_user,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        original_filename="seed-photo.jpg",
        visible_to_customer=True,
    )
    hidden_document = EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        actor_role=EvidenceDocument.ActorRole.OPS,
        kind=EvidenceDocument.DocumentKind.RESPONSE,
        original_filename="ops-internal.txt",
        visible_to_customer=False,
        visible_to_merchant=False,
    )
    client.force_authenticate(user=customer_user)

    response = client.get(f"/api/returns/{return_case.pk}/documents/")

    assert response.status_code == 200
    returned_filenames = [item["original_filename"] for item in response.data]
    assert visible_document.original_filename in returned_filenames
    assert hidden_document.original_filename not in returned_filenames


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
def test_live_returns_documents_post_endpoint_uploads_customer_evidence(
    monkeypatch,
) -> None:
    """The main returns API should expose customer evidence uploads."""
    client = APIClient()
    return_case = ReturnCaseFactory()
    customer_user = return_case.customer.user
    _ensure_group("customer").user_set.add(customer_user)

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_authenticate(user=customer_user)

    response = client.post(
        f"/api/returns/{return_case.pk}/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Visible damage",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["kind"] == "evidence"
    assert response.data["actor_role"] == "customer"
    assert response.data["notes"] == "Visible damage"
