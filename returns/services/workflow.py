"""Compatibility wrappers for legacy return-workflow service imports."""

from __future__ import annotations

from typing import Any

from returns.models import CaseEvent, CaseNote, ReturnCase
from returns.services.cases import (
    ReturnCaseWorkflowError,
    StatusUpdateInput,
    add_case_note,
    update_return_case_status,
)


def update_case_status_and_priority(
    case: ReturnCase,
    actor,
    cleaned_data: dict[str, Any],
) -> ReturnCase:
    """Adapt legacy status-update calls to the canonical workflow service."""

    priority = cleaned_data.get("priority")
    return update_return_case_status(
        actor=actor,
        case=case,
        input_data=StatusUpdateInput(
            status=cleaned_data["status"],
            priority=priority,
        ),
    )


def request_more_information(
    case: ReturnCase,
    actor,
    cleaned_data: dict[str, Any],
) -> CaseEvent:
    """Adapt legacy info-request calls to the canonical waiting-state workflow."""

    recipient = cleaned_data["recipient"]
    status = (
        ReturnCase.Status.WAITING_CUSTOMER
        if recipient == "customer"
        else ReturnCase.Status.WAITING_MERCHANT
    )
    note = f"Requested additional information from {recipient}: {cleaned_data['message']}"

    update_return_case_status(
        actor=actor,
        case=case,
        input_data=StatusUpdateInput(
            status=status,
            note=note,
        ),
    )
    event = case.events.order_by("-created_at", "-id").first()
    if event is None:
        raise ReturnCaseWorkflowError("Expected a workflow event after requesting information.")
    return event


def add_internal_note(
    case: ReturnCase,
    actor,
    cleaned_data: dict[str, Any],
) -> CaseNote:
    """Adapt legacy note-creation calls to the canonical note service."""

    return add_case_note(
        actor=actor,
        case=case,
        body=cleaned_data["body"],
    )
