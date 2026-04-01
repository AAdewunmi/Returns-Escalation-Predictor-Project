"""Tests for returns domain models."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import EvidenceDocument, ReturnCase, build_document_upload_path
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory


@pytest.mark.django_db
def test_return_case_string_representation():
    """ReturnCase.__str__ should include the order reference."""
    customer_user = get_user_model().objects.create_user(
        username="customer-for-return",
        password="password123",
    )
    merchant_user = get_user_model().objects.create_user(
        username="merchant-for-return",
        password="password123",
    )
    customer = CustomerProfile.objects.create(
        user=customer_user,
        external_reference="cust-ret-001",
        display_name="Customer Return",
    )
    merchant = MerchantProfile.objects.create(
        user=merchant_user,
        merchant_code="mrc-ret-001",
        display_name="Merchant Return",
        support_email="merchant-return@example.com",
    )
    case = ReturnCase.objects.create(
        customer=customer,
        merchant=merchant,
        order_reference="ORD-RET-001",
        item_category="Electronics",
        return_reason="Damaged",
        customer_message="Box arrived broken.",
        order_value=Decimal("149.99"),
        delivery_date=date(2026, 3, 1),
    )

    assert str(case) == "ReturnCase<ORD-RET-001>"


@pytest.mark.django_db
def test_build_document_upload_path_uses_case_kind_and_date() -> None:
    """Upload paths should include the case, kind, and created-at partition."""
    document = EvidenceDocumentFactory(
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
    )

    path = build_document_upload_path(document, "Damage Photo.JPG")

    assert path.startswith(f"return-cases/{document.return_case_id}/evidence/")
    assert f"/{document.created_at:%Y/%m}/" in path
    assert path.endswith(".jpg")
    assert "damage-photo-" in path


@pytest.mark.django_db
def test_build_document_upload_path_handles_blank_stem_and_unsaved_document() -> None:
    """Unsaved documents should still produce a stable fallback upload path."""
    return_case = ReturnCaseFactory()
    uploaded_by = get_user_model().objects.create_user(username="doc-user")
    document = EvidenceDocument(
        return_case=return_case,
        uploaded_by=uploaded_by,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        file_path="",
        original_filename="",
        content_type="",
        byte_size=0,
    )

    path = build_document_upload_path(document, ".pdf")

    assert path.startswith(f"return-cases/{return_case.pk}/")
    assert "/evidence/" in path
    assert "/pdf-" in path
    assert "." not in Path(path).name


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/returnhub-test-media")
def test_evidence_document_save_populates_file_metadata() -> None:
    """Saving with a file should backfill stable metadata fields."""
    upload = SimpleUploadedFile(
        "Damage Photo.JPG",
        b"evidence-bytes",
        content_type="image/jpeg",
    )
    return_case = ReturnCaseFactory()
    document = EvidenceDocument(
        return_case=return_case,
        uploaded_by=return_case.customer.user,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        file=upload,
        file_path="",
        original_filename="",
        content_type="",
        byte_size=0,
        checksum_sha256="",
        notes="",
    )

    document.save()

    assert document.file_path.startswith(
        f"return-cases/{document.return_case_id}/{document.kind}/{document.created_at:%Y/%m}/"
    )
    assert document.original_filename == "Damage Photo.JPG"
    assert document.file_path == document.file.name
    assert document.content_type == "image/jpeg"
    assert document.byte_size == len(b"evidence-bytes")
    assert document.checksum_sha256 == hashlib.sha256(b"evidence-bytes").hexdigest()


@pytest.mark.django_db
def test_evidence_document_save_without_file_preserves_existing_metadata() -> None:
    """Saving without a file should keep explicitly provided metadata intact."""
    return_case = ReturnCaseFactory()
    document = EvidenceDocument(
        return_case=return_case,
        uploaded_by=return_case.customer.user,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        file=None,
        file_path="evidence/manual-entry.pdf",
        original_filename="manual-entry.pdf",
        content_type="application/pdf",
        byte_size=123,
        checksum_sha256="abc123",
        notes="",
    )

    document.save()

    assert not document.file
    assert document.file_path == "evidence/manual-entry.pdf"
    assert document.original_filename == "manual-entry.pdf"
    assert document.content_type == "application/pdf"
    assert document.byte_size == 123
    assert document.checksum_sha256 == "abc123"
