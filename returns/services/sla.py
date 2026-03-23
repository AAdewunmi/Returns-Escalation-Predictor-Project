# path: returns/services/sla.py
"""SLA calculation services for ReturnHub return cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping

from django.db import transaction
from django.utils import timezone

from returns.models import ReturnCase


@dataclass(frozen=True)
class SlaWindow:
    """Concrete SLA window values for a given queue priority."""

    first_response_hours: int
    resolution_hours: int


SLA_WINDOWS: Mapping[str, SlaWindow] = {
    "low": SlaWindow(first_response_hours=72, resolution_hours=240),
    "normal": SlaWindow(first_response_hours=48, resolution_hours=120),
    "high": SlaWindow(first_response_hours=24, resolution_hours=72),
    "urgent": SlaWindow(first_response_hours=8, resolution_hours=24),
}

TERMINAL_STATUSES = {"approved", "rejected", "cancelled"}


def get_sla_window(priority: str) -> SlaWindow:
    """Return the configured SLA window for the supplied priority."""

    return SLA_WINDOWS.get(priority, SLA_WINDOWS["normal"])


def calculate_first_response_due_at(
    priority: str,
    *,
    reference_time: datetime | None = None,
) -> datetime:
    """Calculate the first-response due timestamp for a priority level."""

    current_time = reference_time or timezone.now()
    window = get_sla_window(priority)
    return current_time + timedelta(hours=window.first_response_hours)


def calculate_resolution_due_at(
    priority: str,
    *,
    reference_time: datetime | None = None,
) -> datetime:
    """Calculate the resolution due timestamp for a priority level."""

    current_time = reference_time or timezone.now()
    window = get_sla_window(priority)
    return current_time + timedelta(hours=window.resolution_hours)


@transaction.atomic
def refresh_case_sla_fields(
    return_case: ReturnCase,
    *,
    reference_time: datetime | None = None,
    save: bool = True,
) -> ReturnCase:
    """
    Refresh SLA fields on a return case.

    The service writes deterministic due dates derived from the current case
    priority. The caller can defer the database save when batching changes.
    """

    return_case.first_response_due_at = calculate_first_response_due_at(
        return_case.priority,
        reference_time=reference_time,
    )
    return_case.resolution_due_at = calculate_resolution_due_at(
        return_case.priority,
        reference_time=reference_time,
    )

    if save:
        return_case.save(
            update_fields=[
                "first_response_due_at",
                "resolution_due_at",
                "updated_at",
            ]
        )

    return return_case


def is_case_breached(
    return_case: ReturnCase,
    *,
    reference_time: datetime | None = None,
) -> bool:
    """Return whether the case has breached its first-response SLA."""

    if return_case.status in TERMINAL_STATUSES:
        return False

    due_at = return_case.first_response_due_at
    if due_at is None:
        return False

    current_time = reference_time or timezone.now()
    return due_at < current_time
