"""Tests for the returns queue service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from returns.models import ReturnCase, RiskScore
from returns.services.queue import (
    QueueFilters,
    build_filter_querystring,
    build_queue_queryset,
    get_queue_summary,
    normalise_page,
    parse_queue_filters,
)
from tests.factories import ReturnCaseFactory


def test_normalise_page_defaults_invalid_values_to_first_page() -> None:
    """Missing, invalid, and non-positive values should map to page one."""

    assert normalise_page(None) == 1
    assert normalise_page("banana") == 1
    assert normalise_page("0") == 1
    assert normalise_page("-2") == 1
    assert normalise_page("3") == 3


def test_parse_queue_filters_normalises_query_params() -> None:
    """Queue filter parsing should trim values and validate risk labels and page."""

    filters = parse_queue_filters(
        {
            "status": " submitted ",
            "priority": " high ",
            "risk_label": " HIGH ",
            "search": "  merchant@example.com  ",
            "page": "2",
        }
    )

    assert filters == QueueFilters(
        status="submitted",
        priority="high",
        risk_label="high",
        search="merchant@example.com",
        page=2,
    )

    invalid_filters = parse_queue_filters({"risk_label": "critical", "page": "zero"})

    assert invalid_filters.risk_label is None
    assert invalid_filters.page == 1


def test_build_filter_querystring_preserves_non_empty_non_page_values() -> None:
    """Pagination querystrings should preserve active filters except the page value."""

    querystring = build_filter_querystring(
        {
            "status": "submitted",
            "priority": "",
            "risk_label": "high",
            "search": "merchant",
            "page": "4",
        }
    )

    assert querystring == "status=submitted&risk_label=high&search=merchant"


@pytest.mark.django_db
def test_build_queue_queryset_applies_filters_annotations_and_ordering() -> None:
    """Queue results should order breached cases first and expose risk annotations."""

    now = datetime(2026, 3, 9, 12, 0, tzinfo=UTC)

    breached = ReturnCaseFactory(
        order_reference="OPS-1001",
        priority=ReturnCase.Priority.URGENT,
        status=ReturnCase.Status.SUBMITTED,
        sla_due_at=now - timedelta(hours=1),
    )
    breached.customer.user.first_name = "Alice"
    breached.customer.user.last_name = "Queue"
    breached.customer.user.email = "alice@example.com"
    breached.customer.user.save(update_fields=["first_name", "last_name", "email"])
    breached.merchant.display_name = "Alpha Merchant"
    breached.merchant.save(update_fields=["display_name"])

    review = ReturnCaseFactory(
        order_reference="OPS-1002",
        priority=ReturnCase.Priority.HIGH,
        status=ReturnCase.Status.IN_REVIEW,
        sla_due_at=now + timedelta(hours=2),
    )
    RiskScore.objects.create(
        case=review,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.82"),
        label="high",
        reason_codes=[],
        scored_at=now - timedelta(minutes=5),
    )

    low_priority = ReturnCaseFactory(
        order_reference="OPS-1003",
        priority=ReturnCase.Priority.LOW,
        status=ReturnCase.Status.WAITING_CUSTOMER,
        sla_due_at=now + timedelta(hours=1),
    )
    RiskScore.objects.create(
        case=low_priority,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.15"),
        label="low",
        reason_codes=[],
        scored_at=now - timedelta(minutes=10),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("returns.services.queue.timezone.now", lambda: now)

        filtered_queryset = build_queue_queryset(
            QueueFilters(
                priority=ReturnCase.Priority.HIGH,
                risk_label="high",
                search="OPS-1002",
            )
        )
        filtered_case = filtered_queryset.get()

        assert filtered_case.pk == review.pk
        assert filtered_case.current_risk_label == "high"
        assert filtered_case.current_risk_score == Decimal("0.82")

        ordered_queryset = build_queue_queryset(QueueFilters())
        ordered_ids = list(ordered_queryset.values_list("id", flat=True))

    assert ordered_ids[:3] == [breached.id, review.id, low_priority.id]


@pytest.mark.django_db
def test_build_queue_queryset_search_matches_related_fields() -> None:
    """Queue search should match order reference, customer identity, and merchant display name."""

    case = ReturnCaseFactory(order_reference="OPS-SEARCH-1")
    case.customer.user.first_name = "Jamie"
    case.customer.user.last_name = "Buyer"
    case.customer.user.email = "jamie@example.com"
    case.customer.user.save(update_fields=["first_name", "last_name", "email"])
    case.merchant.display_name = "Searchable Merchant"
    case.merchant.save(update_fields=["display_name"])

    assert list(build_queue_queryset(QueueFilters(search="OPS-SEARCH-1"))) == [case]
    assert list(build_queue_queryset(QueueFilters(search="Jamie"))) == [case]
    assert list(build_queue_queryset(QueueFilters(search="jamie@example.com"))) == [case]
    assert list(build_queue_queryset(QueueFilters(search="Searchable Merchant"))) == [case]


@pytest.mark.django_db
def test_get_queue_summary_counts_current_status_names() -> None:
    """Queue summaries should count the current return-case statuses."""

    ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED)
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)
    ReturnCaseFactory(status=ReturnCase.Status.WAITING_CUSTOMER)
    ReturnCaseFactory(status=ReturnCase.Status.WAITING_MERCHANT)
    ReturnCaseFactory(status=ReturnCase.Status.APPROVED)

    summary = get_queue_summary(ReturnCase.objects.all())

    assert summary == {
        "total": 5,
        "submitted": 1,
        "waiting_customer": 1,
        "waiting_merchant": 1,
        "in_review": 1,
        "approved": 1,
        "rejected": 0,
    }
