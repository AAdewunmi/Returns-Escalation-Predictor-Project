# path: returns/forms_customer.py
"""Customer-facing forms for the ReturnHub customer portal."""

from django import forms


class CustomerEvidenceUploadForm(forms.Form):
    """Allow a customer to upload one evidence file and an optional description."""

    evidence_file = forms.FileField(
        label="Evidence file",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        label="What does this file show?",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Explain what this image or document adds to the case.",
            }
        ),
    )
