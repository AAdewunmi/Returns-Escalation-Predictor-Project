# path: console/views.py
"""Authenticated shell views for ReturnHub role consoles."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView

from common.pagination import paginate_queryset
from returns.models import ReturnCase
from returns.services.queue import build_queue_queryset, get_queue_summary, parse_queue_filters

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
