# path: apps/returns/services/queue.py
"""Queue query and filter services for the ReturnHub ops surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlencode

from django.db.models import (
    Case,
    CharField,
    Count,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.utils import timezone

from ml import RiskScore
from returns.models import ReturnCase

QUEUE_PAGE_SIZE = 15
RISK_LABELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class QueueFilters:
    """Immutable filter object used by the API and server-rendered queue."""

    status: str | None = None
    priority: str | None = None
    risk_label: str | None = None
    search: str = ""
    page: int = 1


def normalise_page(raw_page: str | None) -> int:
    """Normalise queue page input to the explicit positive integer contract."""

    try:
        page = int(raw_page or "1")
    except (TypeError, ValueError):
        return 1

    if page <= 0:
        return 1

    return page


def parse_queue_filters(params: Mapping[str, str]) -> QueueFilters:
    """Parse validated queue filters from request query parameters."""

    status = (params.get("status") or "").strip() or None
    priority = (params.get("priority") or "").strip() or None
    risk_label = (params.get("risk_label") or "").strip().lower() or None
    search = (params.get("search") or "").strip()

    if risk_label not in RISK_LABELS:
        risk_label = None

    return QueueFilters(
        status=status,
        priority=priority,
        risk_label=risk_label,
        search=search,
        page=normalise_page(params.get("page")),
    )


def build_filter_querystring(
    params: Mapping[str, str],
    *,
    exclude: tuple[str, ...] = ("page",),
) -> str:
    """Build a filter-preserving querystring fragment for pagination links."""

    preserved_items = []
    for key, value in params.items():
        if key in exclude:
            continue
        if value in ("", None):
            continue
        preserved_items.append((key, value))

    return urlencode(preserved_items)


def build_queue_queryset(filters: QueueFilters) -> QuerySet[ReturnCase]:
    """
    Build the canonical ops queue queryset.

    Ordering is explicit and stable. Filters are applied before later
    pagination. Risk values are annotated from the latest persisted score.
    """

    current_time = timezone.now()
    latest_risk_scores = RiskScore.objects.filter(
        return_case=OuterRef("pk")
    ).order_by("-created_at")

    queryset = (
        ReturnCase.objects.select_related(
            "customer__user",
            "merchant__user",
        )
        .annotate(
            current_risk_score=Subquery(latest_risk_scores.values("score")[:1]),
            current_risk_label=Subquery(
                latest_risk_scores.values("label")[:1],
                output_field=CharField(),
            ),
            priority_rank=Case(
                When(priority="urgent", then=Value(4)),
                When(priority="high", then=Value(3)),
                When(priority="normal", then=Value(2)),
                When(priority="low", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            breached_rank=Case(
                When(
                    first_response_due_at__lt=current_time,
                    status__in=[
                        "submitted",
                        "awaiting_customer",
                        "awaiting_merchant",
                        "under_review",
                    ],
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
    )

    if filters.status:
        queryset = queryset.filter(status=filters.status)

    if filters.priority:
        queryset = queryset.filter(priority=filters.priority)

    if filters.risk_label:
        queryset = queryset.filter(current_risk_label=filters.risk_label)

    if filters.search:
        queryset = queryset.filter(
            Q(public_case_reference__icontains=filters.search)
            | Q(order_number__icontains=filters.search)
            | Q(customer__user__first_name__icontains=filters.search)
            | Q(customer__user__last_name__icontains=filters.search)
            | Q(customer__user__email__icontains=filters.search)
            | Q(merchant__display_name__icontains=filters.search)
        )

    return queryset.order_by(
        "-breached_rank",
        "-priority_rank",
        "first_response_due_at",
        "created_at",
        "id",
    )


def get_queue_summary(queryset: QuerySet[ReturnCase]) -> dict[str, int]:
    """Return lightweight queue summary counts for ops-facing surfaces."""

    status_counts = queryset.values("status").annotate(total=Count("id"))
    summary = {
        "total": queryset.count(),
        "submitted": 0,
        "awaiting_customer": 0,
        "awaiting_merchant": 0,
        "under_review": 0,
        "approved": 0,
        "rejected": 0,
    }

    for row in status_counts:
        summary[row["status"]] = row["total"]

    return summary
