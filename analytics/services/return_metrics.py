# path: analytics/services/return_metrics.py
"""Metrics aggregation services for ReturnHub analytics endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.db.models import Count
from returns.models import ReturnCase


class ReturnMetricsError(ValueError):
    """Raised when analytics date inputs are invalid."""


@dataclass(frozen=True)
class ReturnMetricsWindow:
    """Structured date window for return analytics."""

    from_date: date
    to_date: date


def build_return_metrics(*, window: ReturnMetricsWindow) -> dict:
    """Aggregate return metrics over a bounded inclusive date range."""
    if window.from_date > window.to_date:
        raise ReturnMetricsError("'from' date must be on or before 'to' date.")

    queryset = ReturnCase.objects.filter(
        created_at__date__gte=window.from_date,
        created_at__date__lte=window.to_date,
    )

    status_counts = {
        row["status"]: row["count"]
        for row in queryset.values("status").order_by("status").annotate(count=Count("id"))
    }
    priority_counts = {
        row["priority"]: row["count"]
        for row in queryset.values("priority").order_by("priority").annotate(count=Count("id"))
    }

    return {
        "from": window.from_date.isoformat(),
        "to": window.to_date.isoformat(),
        "total_cases": queryset.count(),
        "status_counts": status_counts,
        "priority_counts": priority_counts,
    }
