# path: ui/views.py
"""Views for the public-facing UI shell."""
from django.views.generic import TemplateView


class BootstrapLandingView(TemplateView):
    """Render a minimal public bootstrap page while the project is scaffolded."""

    template_name = "public/boot.html"
