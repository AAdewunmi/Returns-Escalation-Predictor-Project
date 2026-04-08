# path: apps/returns/services/workflow.py
"""Workflow mutation services for the returns domain."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.returns.models import CaseEvent, CaseNote, ReturnCase


@transaction.atomic
def update_case_status_and_priority(case: ReturnCase, actor, cleaned_data: dict[str, Any]) -> ReturnCase:
    """Persist a status and priority update and emit an audit event if the state changed."""
    previous_status = case.status
    previous_priority = case.priority

    case.status = cleaned_data["status"]
    case.priority = cleaned_data["priority"]
    case.save(update_fields=["status", "priority", "updated_at"])

    if previous_status != case.status or previous_priority != case.priority:
        CaseEvent.objects.create(
            case=case,
            actor=actor,
            event_type="ops_case_updated",
            summary=(
                f"Status {previous_status} → {case.status}; "
                f"priority {previous_priority} → {case.priority}"
            ),
        )

    return case


@transaction.atomic
def request_more_information(case: ReturnCase, actor, cleaned_data: dict[str, Any]) -> CaseEvent:
    """Persist an append-only event requesting more information from an external party."""
    recipient = cleaned_data["recipient"]
    message = cleaned_data["message"]

    return CaseEvent.objects.create(
        case=case,
        actor=actor,
        event_type="info_requested",
        summary=f"Requested more information from {recipient}: {message}",
    )


@transaction.atomic
def add_internal_note(case: ReturnCase, actor, cleaned_data: dict[str, Any]) -> CaseNote:
    """Persist an internal note and emit a paired audit event."""
    note = CaseNote.objects.create(
        case=case,
        author=actor,
        body=cleaned_data["body"],
        visibility="internal",
    )

    CaseEvent.objects.create(
        case=case,
        actor=actor,
        event_type="note_added",
        summary=f"Internal note added by {actor.get_full_name() or actor.email}",
    )

    return note
