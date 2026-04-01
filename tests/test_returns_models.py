"""Tests for returns domain models."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import (
    EvidenceDocument,
    ReturnCase,
    _calculate_file_checksum,
    build_document_upload_path,
)
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory


class FileWithoutTellOrSeek:
    """Minimal file-like object for checksum branch coverage."""

    closed = True

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.open_called = False
        self.close_called = False

    def open(self, mode: str) -> None:
        self.open_called = True

    def close(self) -> None:
        self.close_called = True

    def chunks(self):
        yield self.payload


class FileWithFailingTellAndSeek:
    """File-like object that raises during tell and seek calls."""

    closed = False

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.seek_calls = 0

    def tell(self) -> int:
        raise OSError("tell failed")

    def seek(self, offset: int) -> None:
        self.seek_calls += 1
        raise ValueError("seek failed")

    def chunks(self):
        yield self.payload


class FileWithFailingRestoreSeek:
    """File-like object that fails when restoring its original position."""

    closed = False

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.seek_calls = 0

    def tell(self) -> int:
        return 7

    def seek(self, offset: int) -> None:
        self.seek_calls += 1
        if self.seek_calls > 1:
            raise ValueError("restore failed")

    def chunks(self):
        yield self.payload


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


@pytest.mark.django_db
def test_evidence_document_save_rejects_unsupported_content_type() -> None:
    """Saving should reject file types outside the allowed evidence contract."""
    upload = SimpleUploadedFile(
        "malware.exe",
        b"not-allowed",
        content_type="application/octet-stream",
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

    with pytest.raises(ValidationError, match="Unsupported document type"):
        document.save()


@pytest.mark.django_db
def test_evidence_document_save_rejects_oversized_files() -> None:
    """Saving should reject files larger than the upload limit."""
    upload = SimpleUploadedFile(
        "huge.pdf",
        b"x",
        content_type="application/pdf",
    )
    upload.size = (10 * 1024 * 1024) + 1
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

    with pytest.raises(ValidationError, match="10 MB upload limit"):
        document.save()


def test_calculate_file_checksum_handles_files_without_tell_or_seek() -> None:
    """Checksum helper should support simple file-like objects."""
    file_obj = FileWithoutTellOrSeek(b"branch-coverage")

    checksum = _calculate_file_checksum(file_obj)

    assert checksum == hashlib.sha256(b"branch-coverage").hexdigest()
    assert file_obj.open_called is True
    assert file_obj.close_called is True


def test_calculate_file_checksum_tolerates_tell_and_initial_seek_failures() -> None:
    """Checksum helper should continue when tell or initial seek raises."""
    file_obj = FileWithFailingTellAndSeek(b"branch-coverage")

    checksum = _calculate_file_checksum(file_obj)

    assert checksum == hashlib.sha256(b"branch-coverage").hexdigest()
    assert file_obj.seek_calls == 1


def test_calculate_file_checksum_tolerates_restore_seek_failures() -> None:
    """Checksum helper should still return a checksum if restore seek fails."""
    file_obj = FileWithFailingRestoreSeek(b"branch-coverage")

    checksum = _calculate_file_checksum(file_obj)

    assert checksum == hashlib.sha256(b"branch-coverage").hexdigest()
    assert file_obj.seek_calls == 2
