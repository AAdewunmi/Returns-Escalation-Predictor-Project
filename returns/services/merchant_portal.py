# path: returns/services/merchant_portal.py
"""Merchant portal query and write services."""

from django.db import transaction
from django.utils import timezone

from apps.accounts.mixins import is_admin_user
from apps.core.pagination import paginate_with_contract
from apps.returns.models import CaseEvent, EvidenceDocument, ReturnCase


def build_merchant_case_page(user, query_params):
    """Return paginated merchant cases and filter context for the merchant portal."""
    queryset = ReturnCase.objects.select_related("customer", "merchant").order_by("-created_at", "-id")

    if not is_admin_user(user):
        queryset = queryset.filter(merchant__user=user)

    status_value = query_params.get("status", "").strip()
    if status_value:
        queryset = queryset.filter(status=status_value)

    page_obj = paginate_with_contract(
        queryset=queryset,
        page_number=query_params.get("page"),
        page_size=15,
    )

    preserved_query_dict = query_params.copy()
    preserved_query_dict.pop("page", None)

    return {
        "cases": page_obj.object_list,
        "page_obj": page_obj,
        "selected_status": status_value,
        "query_string": preserved_query_dict.urlencode(),
    }


def get_merchant_case_for_user(user, case_pk):
    """Return a merchant-visible case or raise 404."""
    queryset = (
        ReturnCase.objects.select_related("customer", "merchant", "risk_score")
        .prefetch_related("documents", "events")
        .order_by("-created_at", "-id")
    )

    if not is_admin_user(user):
        queryset = queryset.filter(merchant__user=user)

    return queryset.get(pk=case_pk)


@transaction.atomic
def submit_merchant_response(return_case, submitted_by, response_note="", response_file=None):
    """Persist a merchant response and append an audit event."""
    document = None

    if response_file:
        document = EvidenceDocument.objects.create(
            return_case=return_case,
            uploaded_by=submitted_by,
            file=response_file,
            original_filename=response_file.name,
            size_bytes=getattr(response_file, "size", 0),
            content_type=getattr(response_file, "content_type", ""),
            kind="merchant_response",
        )

    CaseEvent.objects.create(
        return_case=return_case,
        actor=submitted_by,
        event_type="merchant_response_submitted",
        message="Merchant submitted a response.",
        payload={
            "response_note": response_note,
            "document_id": str(document.pk) if document else None,
            "document_name": response_file.name if response_file else None,
            "submitted_at": timezone.now().isoformat(),
        },
    )

    return document
