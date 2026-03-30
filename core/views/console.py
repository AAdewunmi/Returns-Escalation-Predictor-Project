# path: core/views/console.py
"""Role-specific console views aligned with the live console shell."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView

from common.pagination import paginate_queryset
from returns.models import ReturnCase
from returns.services.queue import build_queue_queryset, get_queue_summary, parse_queue_filters


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


class OpsConsoleView(RoleRequiredMixin, TemplateView):
    """Ops console shell for the server-rendered return queue."""

    template_name = "console/ops_dashboard.html"
    allowed_groups = ("Ops", "Admin")

    def get_context_data(self, **kwargs):
        """Build the ops queue context."""
        context = super().get_context_data(**kwargs)
        queue_filters = parse_queue_filters(self.request.GET)
        queryset = build_queue_queryset(queue_filters)
        pagination = paginate_queryset(queryset, self.request.GET.get("page"))
        context["page_title"] = "Ops Console"
        context["queue_filters"] = queue_filters
        context["queue_summary"] = get_queue_summary(queryset)
        context["pagination"] = pagination
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
        return context
