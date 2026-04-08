# path: returns/ops_forms.py
"""Form objects used by the ops workflow surface."""

from __future__ import annotations

from django import forms

from apps.returns.models import ReturnCase


class OpsCaseUpdateForm(forms.ModelForm):
    """Form for status and priority updates from the ops detail page."""

    class Meta:
        """Metadata for the status and priority update form."""

        model = ReturnCase
        fields = ["status", "priority"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class OpsRequestInfoForm(forms.Form):
    """Form for requesting more information from the customer or merchant."""

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


class OpsNoteForm(forms.Form):
    """Form for internal ops-only notes."""

    body = forms.CharField(
        min_length=5,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Add an internal note for the ops team.",
            }
        ),
    )
