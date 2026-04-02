# path: web/urls.py
"""
Server-rendered web routes for ReturnHub.
"""

from __future__ import annotations

from django.urls import path

from apps.web.views.cases import CaseDetailView, CaseDocumentUploadView
from apps.web.views.public import LandingPageView

urlpatterns = [
    path("", LandingPageView.as_view(), name="web-landing"),
    path("cases/<uuid:case_id>/", CaseDetailView.as_view(), name="web-case-detail"),
    path(
        "cases/<uuid:case_id>/documents/upload/",
        CaseDocumentUploadView.as_view(),
        name="web-case-document-upload",
    ),
]
