# path: console/views.py
"""Authenticated shell views for ReturnHub role consoles."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.generic import TemplateView

from common.pagination import paginate_queryset
from returns.models import ReturnCase
from returns.ops_forms import OpsCaseUpdateForm, OpsNoteForm, OpsRequestInfoForm
from returns.services.cases import (
    ReturnCaseWorkflowError,
    add_case_note,
    update_return_case_status,
)
from returns.services.ops_case_detail import build_ops_case_detail_context
from returns.services.queue import build_queue_queryset, get_queue_summary, parse_queue_filters
from ui.forms import CaseDocumentUploadForm

CUSTOMER_TIMELINE_ITEMS = (
    {
        "title": "See your own cases",
        "body": (
            "Keep customer-linked returns visible in one place while later "
            "sprints add deeper case actions."
        ),
    },
    {
        "title": "Track progress clearly",
        "body": (
            "Status, messages, and recent activity stay inside the same " "branded console shell."
        ),
    },
    {
        "title": "Prepare for evidence flows",
        "body": (
            "This layout leaves room for uploads, document review, and richer "
            "case detail without changing the frame."
        ),
    },
)

MERCHANT_TIMELINE_ITEMS = (
    {
        "title": "Review linked cases",
        "body": (
            "Keep merchant-linked returns grouped together in the same "
            "operational frame used across ReturnHub."
        ),
    },
    {
        "title": "Stay in shared workflow context",
        "body": (
            "Case summaries remain visible while later sprints add merchant "
            "responses and supporting documents."
        ),
    },
    {
        "title": "Grow into response handling",
        "body": (
            "The shared layout is ready for merchant-side actions without "
            "duplicating the surrounding shell."
        ),
    },
)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require the current user to belong to one of the configured groups."""

    allowed_groups: tuple[str, ...] = ()
    raise_exception = True

    def test_func(self) -> bool:
        """Validate group membership for the current request."""
        user = self.request.user
        return user.is_superuser or any(
            user.groups.filter(name__iexact=group_name).exists()
            for group_name in self.allowed_groups
        )


class AdminConsoleView(RoleRequiredMixin, TemplateView):
    """In-product admin console shell."""

    template_name = "console/admin_dashboard.html"
    allowed_groups = ("Admin",)

    def get_context_data(self, **kwargs):
        """Build the admin dashboard context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Admin Console"
        context["total_cases"] = ReturnCase.objects.count()
        return context


class BaseOpsQueueView(RoleRequiredMixin, TemplateView):
    """Shared ops queue context for the server-rendered console shell."""

    allowed_groups = ("Ops", "Admin")

    def get_context_data(self, **kwargs):
        """Build the ops queue context."""
        context = super().get_context_data(**kwargs)
        queue_filters = parse_queue_filters(self.request.GET)
        queryset = build_queue_queryset(queue_filters)
        pagination = paginate_queryset(queryset, self.request.GET.get("page"))
        context.update(
            {
                "page_title": "Ops Console",
                "queue_filters": queue_filters,
                "queue_summary": get_queue_summary(queryset),
                "pagination": pagination,
                "queue_reset_url": self.request.path,
            }
        )
        return context


class OpsConsoleView(BaseOpsQueueView):
    """Ops console shell for the server-rendered return queue."""

    template_name = "console/ops_dashboard.html"


class OpsQueueView(OpsConsoleView):
    """Standalone ops queue page with HTMX table partial support."""

    template_name = "ops/queue.html"
    partial_template_name = "ops/partials/_queue_table.html"

    def get_template_names(self):
        """Render the table partial for HTMX requests."""

        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        """Adjust the page title and HTMX settings for the standalone queue route."""

        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ops Queue"
        context["queue_hx_url"] = self.request.path
        context["queue_hx_target"] = "#ops-queue-table"
        return context


class OpsCaseDetailView(RoleRequiredMixin, TemplateView):
    """Standalone ops case detail page aligned with the queue shell."""

    template_name = "ops/case_detail.html"
    allowed_groups = ("Ops", "Admin")

    def _get_action_forms(
        self,
        *,
        return_case: ReturnCase,
        data=None,
        action: str = "",
    ) -> dict[str, object]:
        """Build bound or unbound forms for the ops action panel."""

        return {
            "case_update_form": OpsCaseUpdateForm(
                data=data if action == "case-update" else None,
                return_case=return_case,
            ),
            "request_info_form": OpsRequestInfoForm(
                data=data if action == "request-info" else None,
            ),
            "note_form": OpsNoteForm(
                data=data if action == "add-note" else None,
            ),
        }

    def _render_action_response(self, *, context: dict, status_code: int) -> JsonResponse:
        """Return refreshed ops detail fragments for inline updates."""

        payload = {
            "case_header_html": render_to_string(
                "ops/partials/_case_header.html",
                context,
                request=self.request,
            ),
            "status_panel_html": render_to_string(
                "ops/partials/_status_panel.html",
                context,
                request=self.request,
            ),
            "timeline_html": render_to_string(
                "ops/partials/_timeline.html",
                context,
                request=self.request,
            ),
            "risk_panel_html": render_to_string(
                "ops/partials/_risk_panel.html",
                context,
                request=self.request,
            ),
            "action_panel_html": render_to_string(
                "ops/partials/_action_panel.html",
                context,
                request=self.request,
            ),
        }
        return JsonResponse(payload, status=status_code)

    def _get_base_context(self) -> dict:
        """Build the shared case-detail context."""

        detail_context = build_ops_case_detail_context(
            case_id=self.kwargs["case_id"],
            actor=self.request.user,
        )
        actor_role = detail_context["actor_role"]
        return {
            **detail_context,
            "page_title": f"Ops Case {detail_context['return_case'].order_reference}",
            "upload_form": CaseDocumentUploadForm(actor_role=actor_role) if actor_role else None,
            "upload_success_message": "",
            "ops_queue_url": reverse("ops:queue"),
            "ops_action_success_message": "",
        }

    def get_context_data(self, **kwargs):
        """Build the shared case detail context for the ops route."""

        context = super().get_context_data(**kwargs)
        context.update(self._get_base_context())
        context.update(
            self._get_action_forms(
                return_case=context["return_case"],
            )
        )
        return context

    def post(self, request, *args, **kwargs):
        """Handle status updates, info requests, and note creation inline."""

        action = request.POST.get("ops_action", "")
        context = self._get_base_context()
        return_case = context["return_case"]
        forms = self._get_action_forms(
            return_case=return_case,
            data=request.POST,
            action=action,
        )

        success_message = ""
        status_code = 200

        try:
            if action == "case-update":
                form = forms["case_update_form"]
                if form.is_valid():
                    fresh_case = ReturnCase.objects.get(pk=return_case.pk)
                    update_return_case_status(
                        actor=request.user,
                        case=fresh_case,
                        input_data=form.to_status_update_input(),
                    )
                    success_message = "Case status updated."
                else:
                    status_code = 400
            elif action == "request-info":
                form = forms["request_info_form"]
                if form.is_valid():
                    update_return_case_status(
                        actor=request.user,
                        case=return_case,
                        input_data=form.to_status_update_input(),
                    )
                    success_message = f"Case moved to waiting on {form.cleaned_data['recipient']}."
                else:
                    status_code = 400
            elif action == "add-note":
                form = forms["note_form"]
                if form.is_valid():
                    add_case_note(
                        actor=request.user,
                        case=return_case,
                        body=form.cleaned_data["body"],
                    )
                    success_message = "Internal note added."
                else:
                    status_code = 400
            else:
                status_code = 400
                forms["note_form"].add_error(None, "Choose a valid ops action.")
        except ReturnCaseWorkflowError as exc:
            status_code = 400
            target_form = {
                "case-update": forms["case_update_form"],
                "request-info": forms["request_info_form"],
                "add-note": forms["note_form"],
            }.get(action, forms["note_form"])
            target_form.add_error(None, str(exc))

        context = self._get_base_context()
        if success_message:
            context.update(self._get_action_forms(return_case=context["return_case"]))
        else:
            context.update(forms)
        context["ops_action_success_message"] = success_message

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return self._render_action_response(context=context, status_code=status_code)

        return self.render_to_response(context, status=status_code)


class CustomerConsoleView(RoleRequiredMixin, TemplateView):
    """Customer console shell."""

    template_name = "console/customer_dashboard.html"
    allowed_groups = ("Customer", "Admin")

    def get_context_data(self, **kwargs):
        """Build the customer dashboard context."""
        context = super().get_context_data(**kwargs)
        queryset = ReturnCase.objects.none()
        if hasattr(self.request.user, "customer_profile"):
            queryset = ReturnCase.objects.filter(
                customer=self.request.user.customer_profile
            ).order_by("-created_at")
        context["page_title"] = "Customer Console"
        context["recent_cases"] = queryset[:5]
        context["customer_timeline_items"] = CUSTOMER_TIMELINE_ITEMS
        context["customer_trust_items"] = (
            "Own-case visibility",
            "Shared case history",
            "Role-aware access",
        )
        context["customer_visual_case_meta_items"] = ("item_category", "delivery_date")
        context["customer_recent_case_meta_items"] = (
            "item_category",
            "return_reason",
            "delivery_date",
        )
        return context


class MerchantConsoleView(RoleRequiredMixin, TemplateView):
    """Merchant console shell."""

    template_name = "console/merchant_dashboard.html"
    allowed_groups = ("Merchant", "Admin")

    def get_context_data(self, **kwargs):
        """Build the merchant dashboard context."""
        context = super().get_context_data(**kwargs)
        queryset = ReturnCase.objects.none()
        if hasattr(self.request.user, "merchant_profile"):
            queryset = ReturnCase.objects.filter(
                merchant=self.request.user.merchant_profile
            ).order_by("-created_at")
        context["page_title"] = "Merchant Console"
        context["recent_cases"] = queryset[:5]
        context["merchant_timeline_items"] = MERCHANT_TIMELINE_ITEMS
        context["merchant_trust_items"] = (
            "Merchant-linked cases",
            "Shared workflow context",
            "Future response handling",
        )
        context["merchant_visual_case_meta_items"] = ("item_category", "order_value")
        context["merchant_recent_case_meta_items"] = (
            "item_category",
            "return_reason",
            "order_value",
        )
        return context
