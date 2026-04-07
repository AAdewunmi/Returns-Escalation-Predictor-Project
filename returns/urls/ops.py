# path: returns/urls/ops.py
"""URL routes for the ops surface."""

from django.urls import path

from console.views import OpsCaseDetailView, OpsQueueView

app_name = "ops"

urlpatterns = [
    path("", OpsQueueView.as_view(), name="queue"),
    path("<int:case_id>/", OpsCaseDetailView.as_view(), name="case-detail"),
]
