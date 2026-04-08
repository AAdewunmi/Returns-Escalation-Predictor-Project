"""Unit tests for server-rendered ops workflow forms."""

from __future__ import annotations

from returns.models import ReturnCase
from returns.ops_forms import OpsCaseUpdateForm, OpsNoteForm, OpsRequestInfoForm


def test_ops_case_update_form_disables_status_when_no_transitions_are_available() -> None:
    """Terminal cases should not offer further status transitions."""

    return_case = ReturnCase(status=ReturnCase.Status.APPROVED, priority=ReturnCase.Priority.MEDIUM)

    form = OpsCaseUpdateForm(return_case=return_case)

    assert form.fields["status"].disabled is True
    assert list(form.fields["status"].choices) == []


def test_ops_case_update_form_rejects_status_not_allowed_for_current_case() -> None:
    """The status form should reject choices outside the current transition set."""

    return_case = ReturnCase(
        status=ReturnCase.Status.SUBMITTED, priority=ReturnCase.Priority.MEDIUM
    )

    form = OpsCaseUpdateForm(
        data={
            "status": ReturnCase.Status.SUBMITTED,
            "priority": ReturnCase.Priority.HIGH,
        },
        return_case=return_case,
    )

    assert form.is_valid() is False
    assert "Select a valid choice." in form.errors["status"][0]


def test_ops_request_info_form_rejects_whitespace_only_message() -> None:
    """Whitespace-only follow-up requests should be rejected."""

    form = OpsRequestInfoForm(
        data={
            "recipient": "customer",
            "message": "           ",
        }
    )

    assert form.is_valid() is False
    assert "This field is required." in form.errors["message"][0]


def test_ops_request_info_form_maps_merchant_recipient_to_waiting_merchant() -> None:
    """Merchant requests should map to the merchant waiting status."""

    form = OpsRequestInfoForm(
        data={
            "recipient": "merchant",
            "message": "Please confirm the return window and replacement stock.",
        }
    )

    assert form.is_valid() is True
    status_input = form.to_status_update_input()
    assert status_input.status == ReturnCase.Status.WAITING_MERCHANT
    assert "Requested additional information from merchant" in status_input.note


def test_ops_note_form_rejects_whitespace_only_body() -> None:
    """Whitespace-only note bodies should be rejected."""

    form = OpsNoteForm(data={"body": "     "})

    assert form.is_valid() is False
    assert "This field is required." in form.errors["body"][0]
