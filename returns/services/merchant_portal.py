"""Merchant portal query and write services."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlencode

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from accounts.mixins import is_admin_user
from common.pagination import paginate_queryset
from returns.models import CaseEvent, EvidenceDocument, ReturnCase
from returns.services.cases import _actor_role
from returns.services.documents import DocumentUploadInput, upload_document_for_case


def _build_preserved_querystring(
    query_params: Mapping[str, str],
    *,
    exclude: tuple[str, ...] = ("page",),
) -> str:
    """Return a stable querystring fragment that preserves active filters."""

    return urlencode(
        [
            (key, value)
            for key, value in query_params.items()
            if key not in exclude and value not in ("", None)
        ]
    )


def build_merchant_case_page(user, query_params: Mapping[str, str]) -> dict[str, object]:
    """Return paginated merchant cases and filter context for the merchant portal."""

    queryset = ReturnCase.objects.select_related(
        "customer__user",
        "merchant__user",
    ).order_by("-created_at", "-id")

    if not is_admin_user(user):
        queryset = queryset.filter(merchant__user=user)

    status_value = (query_params.get("status") or "").strip().lower()
    if status_value:
        queryset = queryset.filter(status=status_value)

    pagination = paginate_queryset(queryset, query_params.get("page"))

    return {
        "cases": pagination.page_obj.object_list,
        "page_obj": pagination.page_obj,
        "pagination": pagination,
        "selected_status": status_value,
        "query_string": _build_preserved_querystring(query_params),
    }


def get_merchant_case_for_user(user, case_pk: int) -> ReturnCase:
    """Return a merchant-visible case or raise 404."""

    documents_queryset = EvidenceDocument.objects.order_by("-created_at", "-id")
    if not is_admin_user(user):
        documents_queryset = documents_queryset.filter(visible_to_merchant=True)

    queryset = ReturnCase.objects.select_related(
        "customer__user",
        "merchant__user",
        "risk_score",
    ).prefetch_related(
        Prefetch("documents", queryset=documents_queryset),
        Prefetch(
            "events",
            queryset=CaseEvent.objects.select_related("actor").order_by("-created_at", "-id"),
        ),
    )

    if not is_admin_user(user):
        queryset = queryset.filter(merchant__user=user)

    return get_object_or_404(queryset, pk=case_pk)


def build_merchant_case_detail_context(user, case_pk: int) -> dict[str, object]:
    """Return merchant case detail context with dashboard-specific signals."""

    return_case = get_merchant_case_for_user(user, case_pk)
    response_history = [
        event
        for event in return_case.events.all()
        if event.event_type == "merchant_response_submitted"
    ]
    merchant_activity = [
        event
        for event in return_case.events.all()
        if event.actor_role == "merchant" or event.event_type == "merchant_response_submitted"
    ]

    return {
        "case": return_case,
        "latest_merchant_response": response_history[0] if response_history else None,
        "merchant_response_history": response_history,
        "merchant_activity": merchant_activity,
    }


@transaction.atomic
def submit_merchant_response(
    return_case,
    submitted_by,
    response_note: str = "",
    response_file=None,
):
    """Persist a merchant response event and optional supporting document."""

    response_note = (response_note or "").strip()
    document = None

    if response_file is not None:
        document = upload_document_for_case(
            return_case=return_case,
            actor=submitted_by,
            upload_input=DocumentUploadInput(
                kind=EvidenceDocument.DocumentKind.RESPONSE,
                uploaded_file=response_file,
                notes=response_note,
            ),
        )

    CaseEvent.objects.create(
        return_case=return_case,
        actor=submitted_by,
        actor_role=_actor_role(submitted_by),
        event_type="merchant_response_submitted",
        payload={
            "response_note": response_note,
            "document_id": str(document.pk) if document else "",
            "document_kind": document.kind if document else "",
            "has_document": document is not None,
        },
    )

    return document
