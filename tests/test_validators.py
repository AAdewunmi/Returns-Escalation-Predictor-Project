# path: tests/test_validators.py
"""
Tests for evidence validation helpers.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.returns.validators import validate_document_content_type, validate_document_size


def test_validate_document_content_type_accepts_pdf():
    """
    PDFs should pass content-type validation.
    """

    uploaded_file = SimpleUploadedFile("receipt.pdf", b"pdf-bytes", content_type="application/pdf")
    validate_document_content_type(uploaded_file)


def test_validate_document_size_rejects_oversized_file():
    """
    Files larger than the configured limit should fail validation.
    """

    uploaded_file = SimpleUploadedFile(
        "large.pdf",
        b"a" * ((10 * 1024 * 1024) + 1),
        content_type="application/pdf",
    )

    with pytest.raises(ValidationError) as exc_info:
        validate_document_size(uploaded_file)

    assert "10 MB upload limit" in str(exc_info.value)
