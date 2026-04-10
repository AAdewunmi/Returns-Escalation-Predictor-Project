# path: accounts/views_auth.py
"""Surface-specific authentication views for ReturnHub."""

from django.contrib.auth.views import LoginView

from .forms import SurfaceAuthenticationForm
from .services.surface_redirects import resolve_post_login_url


class SurfaceLoginView(LoginView):
    """Base login view for a specific product surface."""

    authentication_form = SurfaceAuthenticationForm
    redirect_authenticated_user = True
    surface = None
    surface_title = ""
    surface_description = ""

    def get_success_url(self):
        """Send the user to the correct surface console or an allowed next path."""
        next_path = self.request.POST.get("next") or self.request.GET.get("next")
        return resolve_post_login_url(
            user=self.request.user,
            requested_surface=self.surface,
            next_path=next_path,
        )

    def get_context_data(self, **kwargs):
        """Expose surface-specific template content for branded login pages."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "surface": self.surface,
                "surface_title": self.surface_title,
                "surface_description": self.surface_description,
            }
        )
        return context


class AdminLoginView(SurfaceLoginView):
    """Login page for administrative users."""

    template_name = "auth/login_admin.html"
    surface = "admin"
    surface_title = "Admin access"
    surface_description = (
        "Use the admin surface to manage platform configuration and open the Django admin."
    )


class OpsLoginView(SurfaceLoginView):
    """Login page for operations users."""

    template_name = "auth/login_ops.html"
    surface = "ops"
    surface_title = "Ops access"
    surface_description = (
        "Use the ops surface to triage returns, review events, and move cases through workflow."
    )


class CustomerLoginView(SurfaceLoginView):
    """Login page for customer users."""

    template_name = "auth/login_customer.html"
    surface = "customer"
    surface_title = "Customer access"
    surface_description = (
        "Use the customer portal to follow case status and upload supporting evidence."
    )


class MerchantLoginView(SurfaceLoginView):
    """Login page for merchant users."""

    template_name = "auth/login_merchant.html"
    surface = "merchant"
    surface_title = "Merchant access"
    surface_description = (
        "Use the merchant portal to review return cases related to your account and respond."
    )
