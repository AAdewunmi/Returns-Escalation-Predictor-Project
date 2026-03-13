# path: ui/views.py
"""Views for the public-facing UI shell."""
from django.http import Http404
from django.views.generic import TemplateView


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


class BootstrapLandingView(TemplateView):
    """Backward-compatible minimal bootstrap view kept during the sprint transition."""

    template_name = "public/landing.html"
