"""URL routes for core operational API endpoints."""

from __future__ import annotations

from django.urls import path

from core.api.views import HealthCheckView

app_name = "core_api"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
]
