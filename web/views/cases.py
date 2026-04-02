# path: web/views/cases.py
"""
Server-rendered case detail views and HTMX upload handlers.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.returns.models import ReturnCase
from apps.returns.services.documents import DocumentUploadInput, resolve_actor_role, upload_document_for_case
from apps.web.forms.documents import CaseDocumentUploadForm


def _actor_can_access_case(user, return_case: ReturnCase) -> bool:
    """
    Return True when the actor is allowed to access the case detail page.
    """

    actor_role = resolve_actor_role(user)
    if actor_role in {"admin", "ops"}:
        return True
    if actor_role == "customer":
        return return_case.customer_profile.user_id == user.id
    if actor_role == "merchant":
        return return_case.merchant_profile.user_id == user.id
    return False


class CaseDetailView(LoginRequiredMixin, View):
    """
    Render the case detail workspace with evidence, events, and latest risk.
    """

    def get(self, request: HttpRequest, case_id) -> HttpResponse:
        """
        Render the case detail template.
        """

        return_case = get_object_or_404(
            ReturnCase.objects.prefetch_related("documents", "events", "risk_scores"),
            id=case_id,
        )
        if not _actor_can_access_case(request.user, return_case):
            raise PermissionDenied("You do not have access to this case.")

        actor_role = resolve_actor_role(request.user)
        form = CaseDocumentUploadForm(actor_role=actor_role)
        latest_risk = return_case.risk_scores.first()

        return render(
            request,
            "cases/detail.html",
            {
                "return_case": return_case,
                "documents": return_case.documents.all(),
                "events": return_case.events.all(),
                "latest_risk": latest_risk,
                "upload_form": form,
                "actor_role": actor_role,
            },
        )


class CaseDocumentUploadView(LoginRequiredMixin, View):
    """
    Handle evidence uploads from the case detail page.
    """

    def post(self, request: HttpRequest, case_id) -> HttpResponse:
        """
        Validate and persist a case document upload.
        """

        return_case = get_object_or_404(ReturnCase, id=case_id)
        if not _actor_can_access_case(request.user, return_case):
            raise PermissionDenied("You do not have access to this case.")

        actor_role = resolve_actor_role(request.user)
        form = CaseDocumentUploadForm(request.POST, request.FILES, actor_role=actor_role)

        if not form.is_valid():
            response = render(
                request,
                "partials/_upload_panel.html",
                {
                    "return_case": return_case,
                    "upload_form": form,
                    "actor_role": actor_role,
                },
                status=422,
            )
            return response

        try:
            upload_document_for_case(
                return_case=return_case,
                actor=request.user,
                upload_input=DocumentUploadInput(
                    document_kind=form.cleaned_data["document_kind"],
                    uploaded_file=form.cleaned_data["file"],
                    note=form.cleaned_data.get("note", ""),
                ),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        messages.success(request, "Document uploaded successfully.")
        return redirect("web-case-detail", case_id=return_case.id)
