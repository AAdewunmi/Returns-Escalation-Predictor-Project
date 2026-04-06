# path: returns/services/ops_queue.py
"""Queue building utilities for the ops surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Prefetch, Q, QuerySet, Value, When
from django.utils import timezone

from apps.returns.models import ReturnCase, RiskScore

OPS_QUEUE_PAGE_SIZE = 15


@dataclass(frozen=True)
class OpsQueueFilters:
    """Represents supported queue filters for the ops surface."""

    status: str | None = None
    priority: str | None = None
    search: str | None = None

    def to_querystring(self, *, include_page: bool = False, page: int | None = None) -> str:
        """Serialise active filters back into a query string."""
        values: dict[str, str] = {}
        if self.status:
            values["status"] = self.status
        if self.priority:
            values["priority"] = self.priority
        if self.search:
            values["search"] = self.search
        if include_page and page is not None:
            values["page"] = str(page)
        return urlencode(values)


def parse_ops_queue_filters(params: Any) -> OpsQueueFilters:
    """Create a filter object from a request query dict."""
    status = (params.get("status") or "").strip() or None
    priority = (params.get("priority") or "").strip() or None
    search = (params.get("search") or "").strip() or None
    return OpsQueueFilters(status=status, priority=priority, search=search)


def _normalise_page_number(raw_page: Any) -> int:
    """Return a safe 1-indexed page number."""
    try:
        page_number = int(raw_page)
    except (TypeError, ValueError):
        return 1
    return 1 if page_number <= 0 else page_number


def _priority_rank_expression() -> Case:
    """Provide deterministic priority ordering for queue pagination."""
    return Case(
        When(priority="high", then=Value(0)),
        When(priority="normal", then=Value(1)),
        When(priority="low", then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )


def build_ops_queue_queryset(filters: OpsQueueFilters) -> QuerySet[ReturnCase]:
    """Return the filtered, fully ordered queryset used by the ops queue."""
    queryset = (
        ReturnCase.objects.select_related(
            "customer",
            "customer__user",
            "merchant",
        )
        .prefetch_related(
            Prefetch(
                "risk_scores",
                queryset=RiskScore.objects.order_by("-created_at"),
                to_attr="prefetched_risk_scores",
            )
        )
        .annotate(priority_rank=_priority_rank_expression())
    )

    if filters.status:
        queryset = queryset.filter(status=filters.status)

    if filters.priority:
        queryset = queryset.filter(priority=filters.priority)

    if filters.search:
        queryset = queryset.filter(
            Q(reference__icontains=filters.search)
            | Q(customer__user__first_name__icontains=filters.search)
            | Q(customer__user__last_name__icontains=filters.search)
            | Q(customer__user__email__icontains=filters.search)
            | Q(merchant__name__icontains=filters.search)
            | Q(return_reason__icontains=filters.search)
        )

    return queryset.order_by("sla_due_at", "priority_rank", "-created_at", "id")


def _latest_risk(case: ReturnCase) -> RiskScore | None:
    """Return the most recent prefetched risk score for a case."""
    prefetched_scores = getattr(case, "prefetched_risk_scores", [])
    return prefetched_scores[0] if prefetched_scores else None


def _page_window(current_page: int, total_pages: int, *, radius: int = 2) -> list[int]:
    """Return a small page-number window around the current page."""
    if total_pages == 0:
        return []
    start = max(1, current_page - radius)
    end = min(total_pages, current_page + radius)
    return list(range(start, end + 1))


def build_ops_queue_context(filters: OpsQueueFilters, raw_page: Any) -> dict[str, Any]:
    """Build the full queue context for the ops page and HTMX partial."""
    queryset = build_ops_queue_queryset(filters)
    paginator = Paginator(queryset, OPS_QUEUE_PAGE_SIZE)
    page_obj = paginator.get_page(_normalise_page_number(raw_page))

    for case in page_obj.object_list:
        case.latest_risk = _latest_risk(case)

    total_count = paginator.count
    current_start = page_obj.start_index() if total_count else 0
    current_end = page_obj.end_index() if total_count else 0

    overdue_count = queryset.filter(sla_due_at__lt=timezone.now()).exclude(
        status__in=["approved", "rejected", "closed"]
    ).count()
    high_priority_count = queryset.filter(priority="high").count()
    awaiting_external_count = queryset.filter(
        status__in=["awaiting_customer", "awaiting_merchant"]
    ).count()

    return {
        "filters": filters,
        "page_obj": page_obj,
        "page_numbers": _page_window(page_obj.number, paginator.num_pages),
        "total_count": total_count,
        "count_line": f"Showing {current_start}-{current_end} of {total_count}",
        "query_string": filters.to_querystring(),
        "summary_cards": [
            {"label": "Visible cases", "value": total_count},
            {"label": "High priority", "value": high_priority_count},
            {"label": "Overdue SLA", "value": overdue_count},
            {"label": "Awaiting reply", "value": awaiting_external_count},
        ],
    }