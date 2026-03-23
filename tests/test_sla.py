# path: tests/services/test_sla.py
"""Tests for SLA calculation services."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from returns.services.sla import (
    calculate_first_response_due_at,
    calculate_resolution_due_at,
    get_sla_window,
    is_case_breached,
    refresh_case_sla_fields,
)
from tests.factories import ReturnCaseFactory


@pytest.mark.django_db
def test_calculate_due_dates_uses_priority_windows() -> None:
    """Urgent cases should receive the shortest deterministic SLA windows."""

    reference_time = datetime(2026, 3, 9, 9, 0, tzinfo=UTC)

    assert calculate_first_response_due_at("urgent", reference_time=reference_time) == datetime(
        2026, 3, 9, 17, 0, tzinfo=UTC
    )
    assert calculate_resolution_due_at("urgent", reference_time=reference_time) == datetime(
        2026, 3, 10, 9, 0, tzinfo=UTC
    )


@pytest.mark.django_db
def test_get_sla_window_falls_back_to_normal_for_unknown_priority() -> None:
    """Unknown priorities should use the normal SLA window."""

    window = get_sla_window("medium")

    assert window.first_response_hours == 48
    assert window.resolution_hours == 120


@pytest.mark.django_db
def test_refresh_case_sla_fields_persists_values() -> None:
    """Refreshing SLA fields should write the persisted SLA due date."""

    reference_time = datetime(2026, 3, 9, 9, 0, tzinfo=UTC)
    return_case = ReturnCaseFactory(priority="high")

    refresh_case_sla_fields(return_case, reference_time=reference_time, save=True)
    return_case.refresh_from_db()

    assert return_case.sla_due_at == datetime(2026, 3, 12, 9, 0, tzinfo=UTC)


@pytest.mark.django_db
def test_refresh_case_sla_fields_can_skip_persistence() -> None:
    """Refreshing without saving should leave the database row unchanged."""

    reference_time = datetime(2026, 3, 9, 9, 0, tzinfo=UTC)
    return_case = ReturnCaseFactory(priority="urgent", sla_due_at=None)

    refresh_case_sla_fields(return_case, reference_time=reference_time, save=False)

    assert return_case.sla_due_at == datetime(2026, 3, 10, 9, 0, tzinfo=UTC)
    return_case.refresh_from_db()
    assert return_case.sla_due_at is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "sla_due_at", "reference_time", "expected"),
    [
        (
            "approved",
            datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
            datetime(2026, 3, 9, 9, 0, tzinfo=UTC),
            False,
        ),
        ("submitted", None, datetime(2026, 3, 9, 9, 0, tzinfo=UTC), False),
        (
            "submitted",
            datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
            datetime(2026, 3, 9, 9, 0, tzinfo=UTC),
            True,
        ),
        (
            "submitted",
            datetime(2026, 3, 9, 10, 0, tzinfo=UTC),
            datetime(2026, 3, 9, 9, 0, tzinfo=UTC),
            False,
        ),
    ],
)
def test_is_case_breached_handles_terminal_missing_and_active_cases(
    status: str,
    sla_due_at: datetime | None,
    reference_time: datetime,
    expected: bool,
) -> None:
    """Breach detection should ignore terminal or unset cases and flag overdue active ones."""

    return_case = ReturnCaseFactory(status=status, sla_due_at=sla_due_at)

    assert is_case_breached(return_case, reference_time=reference_time) is expected
