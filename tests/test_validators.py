"""Tests for evidence validation helpers."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from returns.validators import (
    MAX_DOCUMENT_SIZE_BYTES,
    validate_document_content_type,
    validate_document_size,
)


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("receipt.pdf", "application/pdf"),
        ("photo.jpg", "image/jpeg"),
        ("image.png", "image/png"),
        ("notes.txt", "text/plain"),
    ],
)
def test_validate_document_content_type_accepts_allowed_types(
    filename: str,
    content_type: str,
) -> None:
    """Allowed evidence content types should pass validation."""
    uploaded_file = SimpleUploadedFile(filename, b"file-bytes", content_type=content_type)

    validate_document_content_type(uploaded_file)


def test_validate_document_content_type_rejects_unsupported_type() -> None:
    """Unsupported content types should fail validation."""
    uploaded_file = SimpleUploadedFile(
        "script.exe",
        b"not-allowed",
        content_type="application/x-msdownload",
    )

    with pytest.raises(ValidationError, match="Unsupported document type"):
        validate_document_content_type(uploaded_file)


def test_validate_document_size_accepts_file_at_limit() -> None:
    """Files at the configured limit should pass validation."""
    uploaded_file = SimpleUploadedFile(
        "limit.pdf",
        b"a" * MAX_DOCUMENT_SIZE_BYTES,
        content_type="application/pdf",
    )

    validate_document_size(uploaded_file)


def test_validate_document_size_rejects_oversized_file() -> None:
    """Files larger than the configured limit should fail validation."""
    uploaded_file = SimpleUploadedFile(
        "large.pdf",
        b"a" * (MAX_DOCUMENT_SIZE_BYTES + 1),
        content_type="application/pdf",
    )

    with pytest.raises(ValidationError, match="10 MB upload limit"):
        validate_document_size(uploaded_file)
