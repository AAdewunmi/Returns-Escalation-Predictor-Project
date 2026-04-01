"""Focused tests for evidence document model behavior."""

from __future__ import annotations

import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from returns.models import EvidenceDocument
from tests.factories import ReturnCaseFactory, UserFactory


@pytest.mark.django_db
@override_settings(MEDIA_ROOT="/tmp/returnhub-test-media")
def test_evidence_document_persists_metadata_from_uploaded_file() -> None:
    """EvidenceDocument should copy stable metadata from the uploaded file."""
    return_case = ReturnCaseFactory()
    actor = UserFactory()
    uploaded_file = SimpleUploadedFile(
        "damage-photo.jpg",
        b"binary-image",
        content_type="image/jpeg",
    )

    document = EvidenceDocument.objects.create(
        return_case=return_case,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        uploaded_by=actor,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        file=uploaded_file,
        file_path="",
        original_filename="",
        content_type="",
        byte_size=0,
        checksum_sha256="",
        notes="",
    )

    document.refresh_from_db()

    assert document.original_filename == "damage-photo.jpg"
    assert document.content_type == "image/jpeg"
    assert document.byte_size == uploaded_file.size
    assert document.checksum_sha256 == hashlib.sha256(b"binary-image").hexdigest()
    assert document.file_path == document.file.name
    assert f"return-cases/{return_case.pk}/evidence/" in document.file.name


@pytest.mark.django_db
def test_evidence_document_rejects_unsupported_content_type() -> None:
    """Domain validation should reject unsupported file types."""
    return_case = ReturnCaseFactory()
    actor = UserFactory()
    uploaded_file = SimpleUploadedFile(
        "script.exe",
        b"not-allowed",
        content_type="application/x-msdownload",
    )

    document = EvidenceDocument(
        return_case=return_case,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        uploaded_by=actor,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        file=uploaded_file,
        file_path="",
        original_filename="",
        content_type="",
        byte_size=0,
        checksum_sha256="",
        notes="",
    )

    with pytest.raises(ValidationError, match="Unsupported document type"):
        document.save()
