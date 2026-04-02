"""Server-rendered forms for the public UI shell."""

from __future__ import annotations

from django import forms

from returns.models import EvidenceDocument


class CaseDocumentUploadForm(forms.Form):
    """Upload form for case-linked evidence and response documents."""

    kind = forms.ChoiceField(choices=EvidenceDocument.DocumentKind.choices)
    file = forms.FileField()
    notes = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Add a short note about this document.",
            }
        ),
    )

    def __init__(self, *args, actor_role: str = "", **kwargs):
        """Restrict document-kind choices to the current actor role."""

        super().__init__(*args, **kwargs)
        self.actor_role = actor_role

        if actor_role == "customer":
            self.fields["kind"].choices = [
                (
                    EvidenceDocument.DocumentKind.EVIDENCE,
                    EvidenceDocument.DocumentKind.EVIDENCE.label,
                )
            ]
        elif actor_role == "merchant":
            self.fields["kind"].choices = [
                (
                    EvidenceDocument.DocumentKind.RESPONSE,
                    EvidenceDocument.DocumentKind.RESPONSE.label,
                )
            ]
        elif actor_role not in {"admin", "ops"}:
            self.fields["kind"].choices = []

        self.fields["kind"].widget.attrs.update({"class": "form-select"})
        self.fields["file"].widget.attrs.update({"class": "form-control"})
        self.fields["notes"].widget.attrs.update({"class": "form-control"})

    def clean_kind(self) -> str:
        """Validate role-specific document-kind restrictions."""

        kind = self.cleaned_data["kind"]

        if self.actor_role == "customer" and kind != EvidenceDocument.DocumentKind.EVIDENCE:
            raise forms.ValidationError("Customers can only upload evidence documents.")

        if self.actor_role == "merchant" and kind != EvidenceDocument.DocumentKind.RESPONSE:
            raise forms.ValidationError("Merchants can only upload response documents.")

        return kind
