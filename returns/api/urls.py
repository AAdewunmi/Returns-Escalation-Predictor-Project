# path: returns/api/urls.py
"""API URL routes for the returns domain."""

from __future__ import annotations

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
    from returns.api.views.analytics import ReturnAnalyticsApiView
except ImportError:
    ReturnAnalyticsApiView = None

try:
    from returns.api.views.audit_export import ReturnCaseAuditExportApiView
except ImportError:
    ReturnCaseAuditExportApiView = None

try:
    from returns.api.views.documents import ReturnCaseDocumentUploadApiView
except ImportError:
    ReturnCaseDocumentUploadApiView = None

app_name = "returns-api"

urlpatterns = [
    path("", ReturnCaseCreateAPIView.as_view(), name="case-create"),
    path("", ReturnCaseCreateAPIView.as_view(), name="return-case-create-api"),
    path("queue/", OpsQueueListAPIView.as_view(), name="ops-queue-api"),
    path("<str:case_id>/", ReturnCaseDetailAPIView.as_view(), name="case-detail"),
    path("<str:case_id>/", ReturnCaseDetailAPIView.as_view(), name="return-case-detail-api"),
    path("<str:case_id>/status/", ReturnCaseStatusAPIView.as_view(), name="case-status"),
    path(
        "<str:case_id>/status/",
        ReturnCaseStatusAPIView.as_view(),
        name="return-case-status-api",
    ),
    path("<str:case_id>/notes/", ReturnCaseNoteAPIView.as_view(), name="case-notes"),
    path("<str:case_id>/notes/", ReturnCaseNoteAPIView.as_view(), name="return-case-note-api"),
    path("<str:case_id>/risk/", ReturnCaseRiskAPIView.as_view(), name="case-risk"),
]

def build_optional_urlpatterns():
    """Return optional placeholder routes for views that may exist later."""

    patterns = []

    if ReturnCaseDocumentUploadApiView is not None:
        patterns.append(
            path(
                "<str:case_id>/documents/",
                ReturnCaseDocumentUploadApiView.as_view(),
                name="return-case-document-api",
            )
        )

    if ReturnAnalyticsApiView is not None:
        patterns.append(
            path(
                "analytics/returns/",
                ReturnAnalyticsApiView.as_view(),
                name="return-analytics-api",
            )
        )

    if ReturnCaseAuditExportApiView is not None:
        patterns.append(
            path(
                "<str:case_id>/audit-export/",
                ReturnCaseAuditExportApiView.as_view(),
                name="return-case-audit-export-api",
            )
        )

    return patterns


urlpatterns += build_optional_urlpatterns()
