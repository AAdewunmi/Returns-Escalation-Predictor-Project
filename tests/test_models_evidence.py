# path: tests/test_models_evidence.py
"""
Tests for evidence document model behaviour.
"""

from __future__ import annotations

import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.returns.models import EvidenceDocument, EvidenceDocumentKind
from apps.returns.tests.factories import ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_evidence_document_persists_metadata_from_uploaded_file():
    """
    EvidenceDocument should copy stable metadata from the uploaded file object.
    """

    return_case = ReturnCaseFactory()
    actor = UserFactory()
    uploaded_file = SimpleUploadedFile(
        "damage-photo.jpg",
        b"binary-image",
        content_type="image/jpeg",
    )

    document = EvidenceDocument.objects.create(
        return_case=return_case,
        document_kind=EvidenceDocumentKind.CUSTOMER_EVIDENCE,
        uploaded_by=actor,
        uploaded_by_role="customer",
        file=uploaded_file,
        original_filename="damage-photo.jpg",
        content_type="image/jpeg",
        size_bytes=uploaded_file.size,
        checksum_sha256=hashlib.sha256(b"binary-image").hexdigest(),
    )

    document.refresh_from_db()

    assert document.original_filename == "damage-photo.jpg"
    assert document.content_type == "image/jpeg"
    assert document.size_bytes == uploaded_file.size
    assert f"return-cases/{return_case.id}/customer_evidence/" in document.file.name


@pytest.mark.django_db
def test_evidence_document_rejects_unsupported_content_type():
    """
    Domain validation should reject unsupported file types.
    """

    return_case = ReturnCaseFactory()
    actor = UserFactory()
    uploaded_file = SimpleUploadedFile(
        "script.exe",
        b"not-allowed",
        content_type="application/x-msdownload",
    )

    document = EvidenceDocument(
        return_case=return_case,
        document_kind=EvidenceDocumentKind.CUSTOMER_EVIDENCE,
        uploaded_by=actor,
        uploaded_by_role="customer",
        file=uploaded_file,
        original_filename="script.exe",
        content_type="application/x-msdownload",
        size_bytes=uploaded_file.size,
        checksum_sha256=hashlib.sha256(b"not-allowed").hexdigest(),
    )

    with pytest.raises(ValidationError) as exc_info:
        document.full_clean()

    assert "Unsupported document type" in str(exc_info.value)