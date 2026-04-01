"""Compatibility API URL routes mirroring the live returns API structure."""

from __future__ import annotations

from importlib import import_module

from django.urls import path

from returns.api.views import (
    OpsQueueListAPIView,
    ReturnCaseCreateAPIView,
    ReturnCaseDetailAPIView,
    ReturnCaseNoteAPIView,
    ReturnCaseRiskAPIView,
    ReturnCaseStatusAPIView,
)

try:
    from api.views.documents import ReturnCaseDocumentUploadApiView
except ImportError:
    ReturnCaseDocumentUploadApiView = None

try:
    from analytics.api.views import ReturnAnalyticsApiView
except ImportError:
    ReturnAnalyticsApiView = None

app_name = "api"

urlpatterns = [
    path("returns/", ReturnCaseCreateAPIView.as_view(), name="api-return-create"),
    path("returns/queue/", OpsQueueListAPIView.as_view(), name="api-ops-queue"),
    path("returns/<str:case_id>/", ReturnCaseDetailAPIView.as_view(), name="api-return-detail"),
    path(
        "returns/<str:case_id>/status/",
        ReturnCaseStatusAPIView.as_view(),
        name="api-return-status-update",
    ),
    path(
        "returns/<str:case_id>/notes/",
        ReturnCaseNoteAPIView.as_view(),
        name="api-return-note-create",
    ),
    path("returns/<str:case_id>/risk/", ReturnCaseRiskAPIView.as_view(), name="api-return-risk"),
]


def build_optional_urlpatterns():
    """Return optional compatibility routes for API views that may exist later."""

    patterns = []
    audit_export_view = None

    if ReturnCaseDocumentUploadApiView is not None:
        patterns.append(
            path(
                "returns/<str:case_id>/documents/",
                ReturnCaseDocumentUploadApiView.as_view(),
                name="api-return-document",
            )
        )

    if ReturnAnalyticsApiView is not None:
        patterns.append(
            path(
                "analytics/returns/",
                ReturnAnalyticsApiView.as_view(),
                name="api-return-analytics",
            )
        )

    try:
        audit_export_view = import_module(
            "returns.api.views.audit_export"
        ).ReturnCaseAuditExportApiView
    except (ImportError, AttributeError):
        audit_export_view = None

    if audit_export_view is not None:
        patterns.append(
            path(
                "returns/<str:case_id>/audit-export/",
                audit_export_view.as_view(),
                name="api-return-audit-export",
            )
        )

    return patterns


urlpatterns += build_optional_urlpatterns()
