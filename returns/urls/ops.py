# path: returns/urls/ops.py
"""URL routes for the ops surface."""

from django.urls import path

from console.views import OpsQueueView

app_name = "ops"

urlpatterns = [
    path("", OpsQueueView.as_view(), name="queue"),
]
