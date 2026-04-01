# path: api/urls.py
"""
API URL routes for ReturnHub.
"""

from __future__ import annotations

from django.urls import path

from apps.api.views.documents import ReturnDocumentView
from apps.api.views.returns import ReturnAuditExportView, ReturnCaseCreateView, ReturnCaseDetailView
from apps.api.views.returns import ReturnNoteCreateView, ReturnStatusUpdateView

urlpatterns = [
    path("returns/", ReturnCaseCreateView.as_view(), name="api-return-create"),
    path("returns/<uuid:case_id>/", ReturnCaseDetailView.as_view(), name="api-return-detail"),
    path(
        "returns/<uuid:case_id>/status/",
        ReturnStatusUpdateView.as_view(),
        name="api-return-status-update",
    ),
    path(
        "returns/<uuid:case_id>/notes/",
        ReturnNoteCreateView.as_view(),
        name="api-return-note-create",
    ),
    path(
        "returns/<uuid:case_id>/documents/",
        ReturnDocumentView.as_view(),
        name="api-return-document",
    ),
    path(
        "returns/<uuid:case_id>/audit-export/",
        ReturnAuditExportView.as_view(),
        name="api-return-audit-export",
    ),
]
