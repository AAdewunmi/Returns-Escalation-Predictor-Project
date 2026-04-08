"""Tests for legacy workflow service compatibility wrappers."""

from __future__ import annotations

import pytest

from returns.models import CaseEvent, CaseNote, ReturnCase
from returns.services.cases import ReturnCaseWorkflowError, StatusUpdateInput
from returns.services.workflow import (
    add_internal_note,
    request_more_information,
    update_case_status_and_priority,
)
from tests.factories import ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_update_case_status_and_priority_delegates_to_canonical_service(monkeypatch) -> None:
    """Legacy status updates should delegate to the canonical case workflow service."""

    actor = UserFactory()
    case = ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED)
    captured: dict[str, object] = {}

    def fake_update_return_case_status(*, actor, case, input_data):
        captured["actor"] = actor
        captured["case"] = case
        captured["input_data"] = input_data
        return case

    monkeypatch.setattr(
        "returns.services.workflow.update_return_case_status",
        fake_update_return_case_status,
    )

    result = update_case_status_and_priority(
        case=case,
        actor=actor,
        cleaned_data={
            "status": ReturnCase.Status.IN_REVIEW,
            "priority": ReturnCase.Priority.HIGH,
        },
    )

    assert result == case
    assert captured["actor"] == actor
    assert captured["case"] == case
    assert captured["input_data"] == StatusUpdateInput(
        status=ReturnCase.Status.IN_REVIEW,
        priority=ReturnCase.Priority.HIGH,
    )


@pytest.mark.django_db
def test_request_more_information_maps_customer_requests_and_returns_latest_event(
    monkeypatch,
) -> None:
    """Customer follow-up requests should map to waiting-customer status and return an event."""

    actor = UserFactory()
    case = ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)
    expected_event = CaseEvent.objects.create(
        return_case=case,
        actor=actor,
        actor_role="ops",
        event_type="status_updated",
        payload={"note": "existing"},
    )
    captured: dict[str, object] = {}

    def fake_update_return_case_status(*, actor, case, input_data):
        captured["actor"] = actor
        captured["case"] = case
        captured["input_data"] = input_data
        return case

    monkeypatch.setattr(
        "returns.services.workflow.update_return_case_status",
        fake_update_return_case_status,
    )

    result = request_more_information(
        case=case,
        actor=actor,
        cleaned_data={
            "recipient": "customer",
            "message": "Please upload a clearer photo of the damaged packaging.",
        },
    )

    assert result == expected_event
    assert captured["actor"] == actor
    assert captured["case"] == case
    assert captured["input_data"] == StatusUpdateInput(
        status=ReturnCase.Status.WAITING_CUSTOMER,
        note=(
            "Requested additional information from customer: "
            "Please upload a clearer photo of the damaged packaging."
        ),
    )


@pytest.mark.django_db
def test_request_more_information_maps_merchant_requests(monkeypatch) -> None:
    """Merchant follow-up requests should map to waiting-merchant status."""

    actor = UserFactory()
    case = ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)
    expected_event = CaseEvent.objects.create(
        return_case=case,
        actor=actor,
        actor_role="ops",
        event_type="status_updated",
        payload={"note": "existing"},
    )
    captured: dict[str, object] = {}

    def fake_update_return_case_status(*, actor, case, input_data):
        captured["input_data"] = input_data
        return case

    monkeypatch.setattr(
        "returns.services.workflow.update_return_case_status",
        fake_update_return_case_status,
    )

    result = request_more_information(
        case=case,
        actor=actor,
        cleaned_data={
            "recipient": "merchant",
            "message": "Please confirm the return window and replacement stock.",
        },
    )

    assert result == expected_event
    assert captured["input_data"] == StatusUpdateInput(
        status=ReturnCase.Status.WAITING_MERCHANT,
        note=(
            "Requested additional information from merchant: "
            "Please confirm the return window and replacement stock."
        ),
    )


@pytest.mark.django_db
def test_request_more_information_raises_when_no_event_is_available(monkeypatch) -> None:
    """The wrapper should fail explicitly if no append-only event can be found."""

    actor = UserFactory()
    case = ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)

    monkeypatch.setattr(
        "returns.services.workflow.update_return_case_status",
        lambda **kwargs: case,
    )

    with pytest.raises(ReturnCaseWorkflowError):
        request_more_information(
            case=case,
            actor=actor,
            cleaned_data={
                "recipient": "customer",
                "message": "Please upload a clearer photo of the damaged packaging.",
            },
        )


@pytest.mark.django_db
def test_add_internal_note_delegates_to_canonical_note_service(monkeypatch) -> None:
    """Legacy note creation should delegate to the canonical note service."""

    actor = UserFactory()
    case = ReturnCaseFactory()
    expected_note = CaseNote(
        return_case=case,
        author=actor,
        body="Flagged for manual review.",
    )
    captured: dict[str, object] = {}

    def fake_add_case_note(*, actor, case, body):
        captured["actor"] = actor
        captured["case"] = case
        captured["body"] = body
        return expected_note

    monkeypatch.setattr(
        "returns.services.workflow.add_case_note",
        fake_add_case_note,
    )

    result = add_internal_note(
        case=case,
        actor=actor,
        cleaned_data={"body": "Flagged for manual review."},
    )

    assert result == expected_note
    assert captured == {
        "actor": actor,
        "case": case,
        "body": "Flagged for manual review.",
    }
