"""Tests for return analytics metric aggregation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from analytics.services.return_metrics import (
    ReturnMetricsError,
    ReturnMetricsWindow,
    build_return_metrics,
)
from returns.models import ReturnCase
from tests.factories import ReturnCaseFactory


@pytest.mark.django_db
def test_build_return_metrics_aggregates_status_and_priority_counts() -> None:
    """The metrics service should return grouped counts for the supplied window."""
    today = timezone.localdate()
    ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED, priority=ReturnCase.Priority.MEDIUM)
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW, priority=ReturnCase.Priority.HIGH)
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW, priority=ReturnCase.Priority.HIGH)

    payload = build_return_metrics(
        window=ReturnMetricsWindow(from_date=today, to_date=today),
    )

    assert payload["from"] == today.isoformat()
    assert payload["to"] == today.isoformat()
    assert payload["total_cases"] == 3
    assert payload["status_counts"] == {
        ReturnCase.Status.IN_REVIEW: 2,
        ReturnCase.Status.SUBMITTED: 1,
    }
    assert payload["priority_counts"] == {
        ReturnCase.Priority.HIGH: 2,
        ReturnCase.Priority.MEDIUM: 1,
    }


def test_build_return_metrics_rejects_inverted_date_window() -> None:
    """The service should reject a date range where from_date is after to_date."""
    today = timezone.localdate()

    with pytest.raises(ReturnMetricsError, match="'from' date must be on or before 'to' date."):
        build_return_metrics(
            window=ReturnMetricsWindow(from_date=today + timedelta(days=1), to_date=today),
        )
