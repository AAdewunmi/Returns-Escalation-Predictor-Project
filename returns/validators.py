# path: returns/validators.py
"""
Domain validation helpers for return-case evidence uploads.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError

ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024


def validate_document_content_type(file_obj) -> None:
    """
    Validate that the uploaded file uses an allowed content type.
    """

    content_type = getattr(file_obj, "content_type", None)
    if content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported document type '{content_type}'. "
            "Allowed types are PDF, JPG, PNG, and plain text."
        )


def validate_document_size(file_obj) -> None:
    """
    Validate that the uploaded file is within the accepted size limit.
    """

    size = getattr(file_obj, "size", 0)
    if size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError("Document exceeds the 10 MB upload limit.")