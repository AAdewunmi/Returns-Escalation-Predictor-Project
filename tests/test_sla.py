# path: tests/services/test_sla.py
"""Tests for SLA calculation services."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

import pytest

from returns.services.sla import (
    calculate_first_response_due_at,
    calculate_resolution_due_at,
    refresh_case_sla_fields,
)
from tests.factories import ReturnCaseFactory


@pytest.mark.django_db
def test_calculate_due_dates_uses_priority_windows() -> None:
    """Urgent cases should receive the shortest deterministic SLA windows."""

    reference_time = datetime(2026, 3, 9, 9, 0, tzinfo=dt_timezone.utc)

    assert calculate_first_response_due_at("urgent", reference_time=reference_time) == datetime(
        2026, 3, 9, 17, 0, tzinfo=dt_timezone.utc
    )
    assert calculate_resolution_due_at("urgent", reference_time=reference_time) == datetime(
        2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc
    )


@pytest.mark.django_db
def test_refresh_case_sla_fields_persists_values() -> None:
    """Refreshing SLA fields should write first-response and resolution due dates."""

    reference_time = datetime(2026, 3, 9, 9, 0, tzinfo=dt_timezone.utc)
    return_case = ReturnCaseFactory(priority="high")

    refresh_case_sla_fields(return_case, reference_time=reference_time, save=True)
    return_case.refresh_from_db()

    assert return_case.first_response_due_at == datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc)
    assert return_case.resolution_due_at == datetime(2026, 3, 12, 9, 0, tzinfo=dt_timezone.utc)
