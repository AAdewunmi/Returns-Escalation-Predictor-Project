# path: returns/services/customer_portal.py
"""Customer portal query and write services."""

from django.db import transaction
from django.utils import timezone

from apps.accounts.mixins import is_admin_user
from apps.core.pagination import paginate_with_contract
from apps.returns.models import CaseEvent, EvidenceDocument, ReturnCase


def build_customer_case_page(user, query_params):
    """Return paginated customer cases and filter context for the customer portal."""
    queryset = ReturnCase.objects.select_related("customer", "merchant").order_by("-created_at", "-id")

    if not is_admin_user(user):
        queryset = queryset.filter(customer__user=user)

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


def get_customer_case_for_user(user, case_pk):
    """Return a customer-visible case or raise 404."""
    queryset = (
        ReturnCase.objects.select_related("customer", "merchant", "risk_score")
        .prefetch_related("documents", "events")
        .order_by("-created_at", "-id")
    )

    if not is_admin_user(user):
        queryset = queryset.filter(customer__user=user)

    return queryset.get(pk=case_pk)


@transaction.atomic
def upload_customer_evidence(return_case, uploaded_by, uploaded_file, description=""):
    """Persist a customer evidence document and append an audit event."""
    document = EvidenceDocument.objects.create(
        return_case=return_case,
        uploaded_by=uploaded_by,
        file=uploaded_file,
        original_filename=uploaded_file.name,
        size_bytes=getattr(uploaded_file, "size", 0),
        content_type=getattr(uploaded_file, "content_type", ""),
        kind="customer_evidence",
    )

    CaseEvent.objects.create(
        return_case=return_case,
        actor=uploaded_by,
        event_type="customer_evidence_uploaded",
        message="Customer uploaded additional evidence.",
        payload={
            "document_id": str(document.pk),
            "document_name": uploaded_file.name,
            "description": description,
            "uploaded_at": timezone.now().isoformat(),
        },
    )

    return document