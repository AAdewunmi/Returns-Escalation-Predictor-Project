# path: ui/urls.py
"""Public UI routes for ReturnHub."""
from django.urls import path

from ui.views import BootstrapLandingView

urlpatterns = [
    path("", BootstrapLandingView.as_view(), name="landing"),
]