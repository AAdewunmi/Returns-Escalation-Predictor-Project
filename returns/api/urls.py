# path: apps/returns/api/urls.py
"""API routes for ReturnHub return workflow."""

from __future__ import annotations

from django.urls import path

from returns.api.views import (
    ReturnCaseCreateAPIView,
    ReturnCaseDetailAPIView,
    ReturnCaseNoteAPIView,
    ReturnCaseStatusAPIView,
)

app_name = "returns-api"

urlpatterns = [
    path("", ReturnCaseCreateAPIView.as_view(), name="case-create"),
    path("<str:case_id>/", ReturnCaseDetailAPIView.as_view(), name="case-detail"),
    path("<str:case_id>/status/", ReturnCaseStatusAPIView.as_view(), name="case-status"),
    path("<str:case_id>/notes/", ReturnCaseNoteAPIView.as_view(), name="case-notes"),
]
