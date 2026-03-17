# path: returns/services/cases.py
"""Service-layer workflow for ReturnHub return cases."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from returns.models import CaseEvent, CaseNote, ReturnCase

STATUS_SUBMITTED: Final[str] = ReturnCase.Status.SUBMITTED
PRIORITY_NORMAL: Final[str] = ReturnCase.Priority.MEDIUM

_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    ReturnCase.Status.SUBMITTED: {
        ReturnCase.Status.IN_REVIEW,
        ReturnCase.Status.WAITING_CUSTOMER,
        ReturnCase.Status.WAITING_MERCHANT,
        ReturnCase.Status.APPROVED,
        ReturnCase.Status.REJECTED,
    },
    ReturnCase.Status.IN_REVIEW: {
        ReturnCase.Status.WAITING_CUSTOMER,
        ReturnCase.Status.WAITING_MERCHANT,
        ReturnCase.Status.APPROVED,
        ReturnCase.Status.REJECTED,
    },
    ReturnCase.Status.WAITING_CUSTOMER: {
        ReturnCase.Status.IN_REVIEW,
        ReturnCase.Status.APPROVED,
        ReturnCase.Status.REJECTED,
    },
    ReturnCase.Status.WAITING_MERCHANT: {
        ReturnCase.Status.IN_REVIEW,
        ReturnCase.Status.APPROVED,
        ReturnCase.Status.REJECTED,
    },
    ReturnCase.Status.APPROVED: set(),
    ReturnCase.Status.REJECTED: set(),
}


class ReturnCaseWorkflowError(ValueError):
    """Raised when a workflow action violates a business rule."""


@dataclass(frozen=True)
class ReturnCaseCreateInput:
    """Structured input for creating a return case."""

    merchant_profile: object
    external_order_ref: str
    item_category: str
    return_reason: str
    customer_message: str
    order_value: Decimal
    delivery_date: object


@dataclass(frozen=True)
class StatusUpdateInput:
    """Structured input for updating case status."""

    status: str
    priority: str | None = None


def _user_in_group(user: AbstractBaseUser, group_name: str) -> bool:
    """Return True when the user belongs to the supplied Django group."""
    return user.is_superuser or user.groups.filter(name__iexact=group_name).exists()


def _require_customer(actor: AbstractBaseUser) -> None:
    """Require the actor to be a customer or superuser."""
    if _user_in_group(actor, "customer") or _user_in_group(actor, "admin"):
        return
    raise PermissionDenied("Only customers or admins can create return cases.")


def _require_ops_or_admin(actor: AbstractBaseUser) -> None:
    """Require the actor to be ops or admin."""
    if _user_in_group(actor, "ops") or _user_in_group(actor, "admin"):
        return
    raise PermissionDenied("Only ops or admins can perform this action.")


def _emit_case_event(
    *,
    case: ReturnCase,
    actor: AbstractBaseUser,
    event_type: str,
    metadata: dict,
) -> CaseEvent:
    """Persist an append-only case event with stable metadata keys."""
    return CaseEvent.objects.create(
        return_case=case,
        actor=actor,
        actor_role=_actor_role(actor),
        event_type=event_type,
        payload=metadata,
    )


def _actor_role(actor: AbstractBaseUser) -> str:
    """Return the actor role label used for append-only workflow events."""
    if _user_in_group(actor, "admin"):
        return "admin"
    if _user_in_group(actor, "ops"):
        return "ops"
    if _user_in_group(actor, "merchant"):
        return "merchant"
    if _user_in_group(actor, "customer"):
        return "customer"
    return ""


@transaction.atomic
def create_return_case(
    *,
    actor: AbstractBaseUser,
    input_data: ReturnCaseCreateInput,
) -> ReturnCase:
    """Create a return case, set deterministic defaults, and emit an audit event."""
    _require_customer(actor)

    if not hasattr(actor, "customer_profile"):
        raise ReturnCaseWorkflowError("Authenticated customer must have a customer profile.")

    case = ReturnCase.objects.create(
        customer=actor.customer_profile,
        merchant=input_data.merchant_profile,
        order_reference=input_data.external_order_ref.strip(),
        item_category=input_data.item_category.strip().lower(),
        return_reason=input_data.return_reason.strip().lower(),
        customer_message=input_data.customer_message.strip(),
        order_value=input_data.order_value,
        delivery_date=input_data.delivery_date,
        status=STATUS_SUBMITTED,
        priority=PRIORITY_NORMAL,
        last_status_changed_at=timezone.now(),
    )

    _emit_case_event(
        case=case,
        actor=actor,
        event_type="case_created",
        metadata={
            "order_reference": case.order_reference,
            "status": case.status,
            "priority": case.priority,
        },
    )
    return case


@transaction.atomic
def update_return_case_status(
    *,
    actor: AbstractBaseUser,
    case: ReturnCase,
    input_data: StatusUpdateInput,
) -> ReturnCase:
    """Update status and optional priority after validating allowed transitions."""
    _require_ops_or_admin(actor)

    current_status = (case.status or "").strip().lower()
    target_status = input_data.status.strip().lower()

    if target_status not in _ALLOWED_STATUS_TRANSITIONS.get(current_status, set()):
        raise ReturnCaseWorkflowError(
            f"Invalid status transition from '{current_status}' to '{target_status}'."
        )

    previous_status = case.status
    previous_priority = case.priority

    case.status = target_status
    update_fields = ["status", "last_status_changed_at", "updated_at"]
    if input_data.priority:
        case.priority = input_data.priority.strip().lower()
        update_fields.append("priority")
    case.last_status_changed_at = timezone.now()

    case.save(update_fields=update_fields)

    _emit_case_event(
        case=case,
        actor=actor,
        event_type="status_updated",
        metadata={
            "previous_status": previous_status,
            "new_status": case.status,
            "previous_priority": previous_priority,
            "new_priority": case.priority,
        },
    )
    return case


@transaction.atomic
def add_case_note(
    *,
    actor: AbstractBaseUser,
    case: ReturnCase,
    body: str,
) -> CaseNote:
    """Persist an ops note and emit a matching audit event."""
    _require_ops_or_admin(actor)

    note_body = body.strip()
    if not note_body:
        raise ReturnCaseWorkflowError("Note body cannot be empty.")

    note = CaseNote.objects.create(return_case=case, author=actor, body=note_body)

    _emit_case_event(
        case=case,
        actor=actor,
        event_type="note_added",
        metadata={"note_id": str(note.pk)},
    )
    return note
