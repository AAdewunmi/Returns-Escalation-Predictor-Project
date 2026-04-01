# path: returns/services/documents.py
"""
Services for uploading and listing evidence documents.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.returns.models import CaseEvent, CaseEventType, EvidenceDocument, EvidenceDocumentKind


@dataclass(frozen=True)
class DocumentUploadInput:
    """
    Input contract for document uploads.
    """

    document_kind: str
    uploaded_file: object
    note: str = ""


def _user_in_group(user, name: str) -> bool:
    """
    Return True when the user belongs to the given Django group.
    """

    return user.is_superuser or Group.objects.filter(user=user, name=name).exists()


def resolve_actor_role(user) -> str:
    """
    Resolve the user's workflow role used in events and permissions.
    """

    if user.is_superuser:
        return "admin"
    if _user_in_group(user, "ops"):
        return "ops"
    if _user_in_group(user, "merchant"):
        return "merchant"
    if _user_in_group(user, "customer"):
        return "customer"
    return "unknown"


def _assert_upload_allowed(return_case, actor, document_kind: str) -> None:
    """
    Assert that the actor can upload the requested document kind to the case.
    """

    actor_role = resolve_actor_role(actor)

    if actor_role == "admin":
        return

    if actor_role == "ops" and document_kind == EvidenceDocumentKind.OPS_ATTACHMENT:
        return

    if actor_role == "customer":
        owns_case = return_case.customer_profile.user_id == actor.id
        if owns_case and document_kind == EvidenceDocumentKind.CUSTOMER_EVIDENCE:
            return

    if actor_role == "merchant":
        related_case = return_case.merchant_profile.user_id == actor.id
        if related_case and document_kind == EvidenceDocumentKind.MERCHANT_RESPONSE:
            return

    raise PermissionError("You do not have permission to upload this document for the case.")


def list_documents_for_case(return_case, actor):
    """
    List documents visible to the actor.
    """

    actor_role = resolve_actor_role(actor)
    queryset = return_case.documents.all()

    if actor_role in {"admin", "ops"}:
        return queryset

    if actor_role == "customer":
        if return_case.customer_profile.user_id != actor.id:
            raise PermissionError("You do not have access to this case.")
        return queryset.filter(visible_to_customer=True)

    if actor_role == "merchant":
        if return_case.merchant_profile.user_id != actor.id:
            raise PermissionError("You do not have access to this case.")
        return queryset.filter(visible_to_merchant=True)

    raise PermissionError("You do not have access to this case.")


@transaction.atomic
def upload_document_for_case(*, return_case, actor, upload_input: DocumentUploadInput) -> EvidenceDocument:
    """
    Upload a document for a return case and emit an audit event.

    The rescore hook is intentionally lightweight and tolerant. If the evidence-aware
    model is not yet trained in a local environment, the upload should still succeed.
    """

    _assert_upload_allowed(return_case, actor, upload_input.document_kind)

    file_bytes = upload_input.uploaded_file.read()
    upload_input.uploaded_file.seek(0)

    actor_role = resolve_actor_role(actor)
    visibility = {
        EvidenceDocumentKind.CUSTOMER_EVIDENCE: (True, True),
        EvidenceDocumentKind.MERCHANT_RESPONSE: (True, True),
        EvidenceDocumentKind.OPS_ATTACHMENT: (False, False),
    }[upload_input.document_kind]

    document = EvidenceDocument.objects.create(
        return_case=return_case,
        document_kind=upload_input.document_kind,
        uploaded_by=actor,
        uploaded_by_role=actor_role,
        file=upload_input.uploaded_file,
        original_filename=upload_input.uploaded_file.name,
        content_type=getattr(upload_input.uploaded_file, "content_type", "application/octet-stream"),
        size_bytes=getattr(upload_input.uploaded_file, "size", 0),
        checksum_sha256=hashlib.sha256(file_bytes).hexdigest(),
        note=upload_input.note,
        visible_to_customer=visibility[0],
        visible_to_merchant=visibility[1],
    )

    CaseEvent.objects.create(
        return_case=return_case,
        event_type=CaseEventType.DOCUMENT_UPLOADED,
        actor=actor,
        actor_role=actor_role,
        payload={
            "document_id": str(document.id),
            "document_kind": document.document_kind,
            "original_filename": document.original_filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
        },
    )

    try:
        from apps.returns.services.risk import score_case_for_escalation

        score_case_for_escalation(return_case=return_case, trigger_source="document_upload")
    except Exception:
        # Uploads must remain available even when the local model artefact is absent.
        pass

    return document
