# path: ui/views.py
"""Views for the public-facing UI shell."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import TemplateView

from returns.models import ReturnCase
from returns.services.documents import (
    DocumentServiceError,
    DocumentUploadInput,
    list_documents_for_case,
    upload_document_for_case,
)
from returns.services.ops_case_detail import (
    build_ops_case_detail_context,
    get_case_detail_actor_role,
    get_case_detail_case,
)
from ui.forms import CaseDocumentUploadForm

SURFACE_CONTENT = {
    "admin": {
        "surface_title": "Admin surface",
        "heading": "Administration entry is reserved and branded.",
        "body": (
            "Sprint 1 reserves the admin entry route so the landing page points at a real, "
            "product-branded destination. Django admin remains available now, while in-product "
            "admin console work and auth routing land in later sprints."
        ),
    },
    "ops": {
        "surface_title": "Ops surface",
        "heading": "Ops entry is reserved for queue-driven work.",
        "body": (
            "This route establishes the future ops login surface and keeps product entry points "
            "coherent from the start. Queue, filtering, status actions, and HTMX interactions "
            "arrive in later sprints."
        ),
    },
    "customer": {
        "surface_title": "Customer surface",
        "heading": "Customer entry is reserved for case tracking.",
        "body": (
            "Sprint 1 gives customers a branded entry point instead of a dead link. Read-only "
            "case status, pagination, and evidence upload workflows arrive once API-first "
            "workflow contracts are in place."
        ),
    },
    "merchant": {
        "surface_title": "Merchant surface",
        "heading": "Merchant entry is reserved for linked case responses.",
        "body": (
            "The merchant portal lands after the workflow and permissions backbone is in place. "
            "This first pass keeps the public information architecture intact and role-specific."
        ),
    },
}


class LandingView(TemplateView):
    """Render the branded public landing page."""

    template_name = "public/landing.html"


class SurfaceEntryView(TemplateView):
    """Render branded placeholder pages for role-specific future login routes."""

    template_name = "public/surface_entry.html"

    def get_context_data(self, **kwargs) -> dict:
        """Return per-surface content for the entry page."""
        context = super().get_context_data(**kwargs)
        surface = kwargs["surface"]

        if surface not in SURFACE_CONTENT:
            raise Http404("Unknown surface.")

        context.update(SURFACE_CONTENT[surface])
        return context


class BootstrapLandingView(LandingView):
    """Backward-compatible minimal bootstrap view kept during the sprint transition."""


class ReturnCaseDetailView(TemplateView):
    """Render a project-aligned return case detail workspace."""

    template_name = "cases/detail.html"

    def _get_upload_form(
        self,
        *,
        actor_role: str,
        data=None,
        files=None,
    ) -> CaseDocumentUploadForm | None:
        """Return a bound or unbound upload form when the actor can upload."""

        if not actor_role:
            return None

        return CaseDocumentUploadForm(data=data, files=files, actor_role=actor_role)

    def get_context_data(self, **kwargs) -> dict:
        """Return case detail context for the workspace template."""

        context = super().get_context_data(**kwargs)
        detail_context = build_ops_case_detail_context(
            case_id=self.kwargs["case_id"],
            actor=self.request.user,
        )

        context.update(
            {
                **detail_context,
                "upload_form": self._get_upload_form(actor_role=detail_context["actor_role"]),
                "upload_success_message": "",
            }
        )
        return context


class ReturnCaseDocumentUploadView(LoginRequiredMixin, View):
    """Handle server-rendered document uploads for the case detail workspace."""

    def _get_return_case(self, case_id: int) -> ReturnCase:
        """Fetch the case for upload handling."""

        return get_case_detail_case(case_id=case_id)

    def _get_actor_role(self, *, return_case: ReturnCase) -> str:
        """Resolve the actor role allowed to upload against this case."""

        try:
            return get_case_detail_actor_role(actor=self.request.user, return_case=return_case)
        except PermissionDenied:
            return ""

    def _render_response(
        self,
        *,
        return_case: ReturnCase,
        upload_form: CaseDocumentUploadForm | None,
        actor_role: str,
        success_message: str = "",
        status_code: int = 200,
    ) -> JsonResponse:
        """Render updated HTML fragments for the upload panel and document table."""

        try:
            documents = list_documents_for_case(
                return_case=return_case,
                actor=self.request.user,
            ).order_by("-created_at", "-id")
        except PermissionDenied:
            documents = return_case.documents.none()

        payload = {
            "upload_panel_html": render_to_string(
                "partials/_upload_panel.html",
                {
                    "upload_form": upload_form,
                    "upload_success_message": success_message,
                    "return_case": return_case,
                    "actor_role": actor_role,
                },
                request=self.request,
            ),
            "document_table_html": render_to_string(
                "partials/_document_table.html",
                {"documents": documents},
                request=self.request,
            ),
        }
        return JsonResponse(payload, status=status_code)

    def post(self, request, case_id: int) -> JsonResponse:
        """Upload a document and return refreshed partial HTML for the page."""

        return_case = self._get_return_case(case_id)
        actor_role = self._get_actor_role(return_case=return_case)

        if not actor_role:
            form = None
            return self._render_response(
                return_case=return_case,
                upload_form=form,
                actor_role="",
                status_code=403,
            )

        form = CaseDocumentUploadForm(request.POST, request.FILES, actor_role=actor_role)
        success_message = ""
        status_code = 200

        if form.is_valid():
            try:
                upload_document_for_case(
                    return_case=return_case,
                    actor=request.user,
                    upload_input=DocumentUploadInput(
                        kind=form.cleaned_data["kind"],
                        uploaded_file=form.cleaned_data["file"],
                        notes=form.cleaned_data["notes"],
                    ),
                )
            except PermissionDenied as exc:
                form.add_error(None, str(exc))
                status_code = 403
            except DocumentServiceError as exc:
                form.add_error(None, str(exc))
                status_code = 400
            else:
                success_message = "Document uploaded successfully."
                form = CaseDocumentUploadForm(actor_role=actor_role)
        else:
            status_code = 400

        return self._render_response(
            return_case=return_case,
            upload_form=form,
            actor_role=actor_role,
            success_message=success_message,
            status_code=status_code,
        )
