"""Customer portal query and write services."""

from __future__ import annotations

from collections.abc import Mapping
from urllib.parse import urlencode

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from accounts.mixins import is_admin_user
from common.pagination import paginate_queryset
from returns.models import CaseEvent, EvidenceDocument, ReturnCase
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


def build_customer_case_page(user, query_params: Mapping[str, str]) -> dict[str, object]:
    """Return paginated customer cases and filter context for the customer portal."""

    queryset = ReturnCase.objects.select_related(
        "customer__user",
        "merchant__user",
    ).order_by("-created_at", "-id")

    if not is_admin_user(user):
        queryset = queryset.filter(customer__user=user)

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


def get_customer_case_for_user(user, case_pk: int) -> ReturnCase:
    """Return a customer-visible case or raise 404."""

    documents_queryset = EvidenceDocument.objects.order_by("-created_at", "-id")
    if not is_admin_user(user):
        documents_queryset = documents_queryset.filter(visible_to_customer=True)

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
        queryset = queryset.filter(customer__user=user)

    return get_object_or_404(queryset, pk=case_pk)


def upload_customer_evidence(return_case, uploaded_by, uploaded_file, description: str = ""):
    """Persist customer evidence using the canonical document upload service."""

    return upload_document_for_case(
        return_case=return_case,
        actor=uploaded_by,
        upload_input=DocumentUploadInput(
            kind=EvidenceDocument.DocumentKind.EVIDENCE,
            uploaded_file=uploaded_file,
            notes=description,
        ),
    )
