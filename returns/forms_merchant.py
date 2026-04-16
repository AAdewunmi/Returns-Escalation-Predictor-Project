# path: returns/forms_merchant.py
"""Merchant-facing forms for response submission."""

from django import forms


class MerchantResponseForm(forms.Form):
    """Allow a merchant to submit a response note and optional document."""

    response_note = forms.CharField(
        label="Response note",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Add context for the ops team or explain the merchant position.",
            }
        ),
    )
    response_file = forms.FileField(
        label="Supporting file",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )

    def clean(self):
        """Require at least one response input."""
        cleaned_data = super().clean()
        if not cleaned_data.get("response_note") and not cleaned_data.get("response_file"):
            raise forms.ValidationError("Add a response note, a supporting file, or both.")
        return cleaned_data
