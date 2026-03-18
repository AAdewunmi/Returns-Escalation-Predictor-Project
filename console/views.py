# path: apps/console/views.py
"""Authenticated shell views for ReturnHub role consoles."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView

from returns.models import ReturnCase


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Require the current user to belong to one of the configured groups."""

    allowed_groups: tuple[str, ...] = ()
    raise_exception = True

    def test_func(self) -> bool:
        """Validate group membership for the current request."""
        user = self.request.user
        return user.is_superuser or user.groups.filter(name__in=self.allowed_groups).exists()


class AdminConsoleView(RoleRequiredMixin, TemplateView):
    """In-product admin console shell."""

    template_name = "console/admin_dashboard.html"
    allowed_groups = ("admin",)

    def get_context_data(self, **kwargs):
        """Build the admin dashboard context."""
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Admin Console"
        context["total_cases"] = ReturnCase.objects.count()
        return context


class OpsConsoleView(RoleRequiredMixin, TemplateView):
    """Ops console shell that will later host queue and case detail surfaces."""

    template_name = "console/ops_dashboard.html"
    allowed_groups = ("ops", "admin")

    def get_context_data(self, **kwargs):
        """Build the ops dashboard context."""
        context = super().get_context_data(**kwargs)
        queryset = ReturnCase.objects.order_by("-created_at")
        context["page_title"] = "Ops Console"
        context["submitted_count"] = queryset.filter(status="submitted").count()
        context["under_review_count"] = queryset.filter(status="under_review").count()
        context["recent_cases"] = queryset[:5]
        return context


class CustomerConsoleView(RoleRequiredMixin, TemplateView):
    """Customer console shell."""

    template_name = "console/customer_dashboard.html"
    allowed_groups = ("customer", "admin")

    def get_context_data(self, **kwargs):
        """Build the customer dashboard context."""
        context = super().get_context_data(**kwargs)
        queryset = ReturnCase.objects.none()
        if hasattr(self.request.user, "customer_profile"):
            queryset = ReturnCase.objects.filter(
                customer_profile=self.request.user.customer_profile
            ).order_by("-created_at")
        context["page_title"] = "Customer Console"
        context["recent_cases"] = queryset[:5]
        return context


class MerchantConsoleView(RoleRequiredMixin, TemplateView):
    """Merchant console shell."""

    template_name = "console/merchant_dashboard.html"
    allowed_groups = ("merchant", "admin")

    def get_context_data(self, **kwargs):
        """Build the merchant dashboard context."""
        context = super().get_context_data(**kwargs)
        queryset = ReturnCase.objects.none()
        if hasattr(self.request.user, "merchant_profile"):
            queryset = ReturnCase.objects.filter(
                merchant_profile=self.request.user.merchant_profile
            ).order_by("-created_at")
        context["page_title"] = "Merchant Console"
        context["recent_cases"] = queryset[:5]
        return context
