"""Services for uploading and listing evidence documents."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db import transaction

from returns.models import CaseEvent, EvidenceDocument, ReturnCase
from returns.services.cases import _actor_role
from returns.services.risk import score_case_and_persist

logger = logging.getLogger(__name__)


class DocumentServiceError(ValueError):
    """Raised when a document workflow action violates a business rule."""


@dataclass(frozen=True)
class DocumentUploadInput:
    """Structured input for document uploads."""

    kind: str
    uploaded_file: object
    notes: str = ""
    visible_to_customer: bool | None = None
    visible_to_merchant: bool | None = None


def _assert_upload_allowed(
    *,
    return_case: ReturnCase,
    actor: AbstractBaseUser,
    kind: str,
) -> str:
    """Validate upload permissions and return the resolved actor role."""

    actor_role = _actor_role(actor)

    if actor_role in {"admin", "ops"}:
        return actor_role

    if actor_role == "customer":
        if (
            return_case.customer.user_id == actor.id
            and kind == EvidenceDocument.DocumentKind.EVIDENCE
        ):
            return actor_role
        raise PermissionDenied("Customers can only upload evidence to their own cases.")

    if actor_role == "merchant":
        if (
            return_case.merchant.user_id == actor.id
            and kind == EvidenceDocument.DocumentKind.RESPONSE
        ):
            return actor_role
        raise PermissionDenied("Merchants can only upload responses to their own cases.")

    raise PermissionDenied("You do not have permission to upload documents for this case.")


def _resolve_visibility(upload_input: DocumentUploadInput) -> tuple[bool, bool]:
    """Resolve default or explicit visibility for the uploaded document."""

    default_customer_visible = upload_input.kind == EvidenceDocument.DocumentKind.EVIDENCE
    default_merchant_visible = upload_input.kind == EvidenceDocument.DocumentKind.RESPONSE

    return (
        upload_input.visible_to_customer
        if upload_input.visible_to_customer is not None
        else default_customer_visible,
        upload_input.visible_to_merchant
        if upload_input.visible_to_merchant is not None
        else default_merchant_visible,
    )


def list_documents_for_case(*, return_case: ReturnCase, actor: AbstractBaseUser):
    """Return the document queryset visible to the requesting actor."""

    actor_role = _actor_role(actor)
    queryset = return_case.documents.all()

    if actor_role in {"admin", "ops"}:
        return queryset

    if actor_role == "customer":
        if return_case.customer.user_id != actor.id:
            raise PermissionDenied("You do not have access to this case.")
        return queryset.filter(visible_to_customer=True)

    if actor_role == "merchant":
        if return_case.merchant.user_id != actor.id:
            raise PermissionDenied("You do not have access to this case.")
        return queryset.filter(visible_to_merchant=True)

    raise PermissionDenied("You do not have access to this case.")


@transaction.atomic
def upload_document_for_case(
    *,
    return_case: ReturnCase,
    actor: AbstractBaseUser,
    upload_input: DocumentUploadInput,
) -> EvidenceDocument:
    """Upload a document, emit an audit event, and trigger a best-effort rescore."""

    if upload_input.kind not in EvidenceDocument.DocumentKind.values:
        raise DocumentServiceError(f"Unsupported document kind '{upload_input.kind}'.")

    actor_role = _assert_upload_allowed(
        return_case=return_case,
        actor=actor,
        kind=upload_input.kind,
    )
    visible_to_customer, visible_to_merchant = _resolve_visibility(upload_input)

    file_bytes = upload_input.uploaded_file.read()
    upload_input.uploaded_file.seek(0)

    document = EvidenceDocument.objects.create(
        return_case=return_case,
        kind=upload_input.kind,
        uploaded_by=actor,
        actor_role=actor_role,
        file=upload_input.uploaded_file,
        file_path="",
        original_filename="",
        content_type="",
        byte_size=0,
        checksum_sha256=hashlib.sha256(file_bytes).hexdigest(),
        notes=upload_input.notes.strip(),
        visible_to_customer=visible_to_customer,
        visible_to_merchant=visible_to_merchant,
    )

    CaseEvent.objects.create(
        return_case=return_case,
        event_type="document_uploaded",
        actor=actor,
        actor_role=actor_role,
        payload={
            "document_id": str(document.pk),
            "kind": document.kind,
            "original_filename": document.original_filename,
            "content_type": document.content_type,
            "byte_size": document.byte_size,
        },
    )

    try:
        score_case_and_persist(return_case, triggered_by="document_uploaded")
    except Exception:
        logger.exception(
            "Risk re-score failed after document upload for case_id=%s",
            return_case.pk,
        )

    return document
