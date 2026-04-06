# path: returns/urls/ops.py
"""URL routes for the ops surface."""

from django.urls import path

from console.views import OpsConsoleView

app_name = "ops"

urlpatterns = [
    path("", OpsConsoleView.as_view(), name="queue"),
]
