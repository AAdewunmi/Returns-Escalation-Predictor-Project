# path: analytics/api/urls.py
"""URL routes for ReturnHub analytics endpoints."""

from __future__ import annotations

from django.urls import path

from analytics.api.views import ReturnAnalyticsAPIView

app_name = "analytics-api"

urlpatterns = [
    path("returns/", ReturnAnalyticsAPIView.as_view(), name="return-analytics"),
]
