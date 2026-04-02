# path: web/forms/documents.py
"""
Forms used for case document uploads in server-rendered surfaces.
"""

from __future__ import annotations

from django import forms

from apps.returns.models import EvidenceDocumentKind


class CaseDocumentUploadForm(forms.Form):
    """
    Upload form that constrains document kind by actor role.
    """

    document_kind = forms.ChoiceField(choices=[])
    file = forms.FileField()
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, actor_role: str, **kwargs):
        """
        Initialise the form with role-specific document kind choices.
        """

        super().__init__(*args, **kwargs)
        choices_by_role = {
            "customer": [(EvidenceDocumentKind.CUSTOMER_EVIDENCE, "Customer evidence")],
            "merchant": [(EvidenceDocumentKind.MERCHANT_RESPONSE, "Merchant response")],
            "ops": [(EvidenceDocumentKind.OPS_ATTACHMENT, "Ops attachment")],
            "admin": list(EvidenceDocumentKind.choices),
        }
        self.fields["document_kind"].choices = choices_by_role.get(actor_role, [])
