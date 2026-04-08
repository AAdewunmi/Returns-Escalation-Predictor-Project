"""Server-rendered forms for the ops case detail workflow."""

from __future__ import annotations

from django import forms

from returns.models import ReturnCase
from returns.services.cases import StatusUpdateInput, get_allowed_status_transitions


class OpsCaseUpdateForm(forms.ModelForm):
    """Update status and priority from the ops case detail page."""

    class Meta:
        model = ReturnCase
        fields = ["status", "priority"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, return_case: ReturnCase, **kwargs):
        """Limit status choices to transitions allowed from the current case state."""

        super().__init__(*args, instance=return_case, **kwargs)
        self.return_case = return_case
        allowed_statuses = get_allowed_status_transitions(current_status=return_case.status)
        self.fields["status"].choices = [
            (value, label)
            for value, label in ReturnCase.Status.choices
            if value in allowed_statuses
        ]
        self.fields["status"].disabled = not bool(allowed_statuses)

    def clean_status(self) -> str:
        """Require an explicit allowed transition for status changes."""

        status = self.cleaned_data["status"]
        if status not in get_allowed_status_transitions(current_status=self.return_case.status):
            raise forms.ValidationError("Select a valid next status for this case.")
        return status

    def to_status_update_input(self) -> StatusUpdateInput:
        """Convert validated data into the shared service input."""

        return StatusUpdateInput(
            status=self.cleaned_data["status"],
            priority=self.cleaned_data["priority"],
        )


class OpsRequestInfoForm(forms.Form):
    """Request additional information from the customer or merchant."""

    recipient = forms.ChoiceField(
        choices=[
            ("customer", "Customer"),
            ("merchant", "Merchant"),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    message = forms.CharField(
        min_length=10,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain what additional information is required.",
            }
        ),
    )

    def clean_message(self) -> str:
        """Reject whitespace-only request messages."""

        message = self.cleaned_data["message"].strip()
        if not message:
            raise forms.ValidationError("Provide a message for the follow-up request.")
        return message

    def to_status_update_input(self) -> StatusUpdateInput:
        """Map the request into the canonical waiting status plus note payload."""

        recipient = self.cleaned_data["recipient"]
        status = (
            ReturnCase.Status.WAITING_CUSTOMER
            if recipient == "customer"
            else ReturnCase.Status.WAITING_MERCHANT
        )
        note = (
            f"Requested additional information from {recipient}: " f"{self.cleaned_data['message']}"
        )
        return StatusUpdateInput(status=status, note=note)


class OpsNoteForm(forms.Form):
    """Create an internal ops-only note."""

    body = forms.CharField(
        min_length=5,
        max_length=4000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add an internal note for the ops team.",
            }
        ),
    )

    def clean_body(self) -> str:
        """Reject whitespace-only note bodies."""

        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Add a note before submitting.")
        return body
