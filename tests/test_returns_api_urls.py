"""Tests for optional returns API URL registration."""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

import returns.api.urls as returns_api_urls


class _StubAPIView(APIView):
    """Simple placeholder API view for URL registration tests."""

    def get(self, request, *args, **kwargs):
        return Response({})


def test_build_optional_urlpatterns_omits_missing_views(monkeypatch) -> None:
    """Optional routes should be skipped when placeholder views are unavailable."""

    monkeypatch.setattr(returns_api_urls, "ReturnCaseDocumentUploadApiView", None)
    monkeypatch.setattr(returns_api_urls, "ReturnAnalyticsApiView", None)
    monkeypatch.setattr(returns_api_urls, "ReturnCaseAuditExportApiView", None)

    patterns = returns_api_urls.build_optional_urlpatterns()

    assert patterns == []


def test_build_optional_urlpatterns_includes_available_views(monkeypatch) -> None:
    """Optional routes should be registered when placeholder views are available."""

    monkeypatch.setattr(returns_api_urls, "ReturnCaseDocumentUploadApiView", _StubAPIView)
    monkeypatch.setattr(returns_api_urls, "ReturnAnalyticsApiView", _StubAPIView)
    monkeypatch.setattr(returns_api_urls, "ReturnCaseAuditExportApiView", _StubAPIView)

    patterns = returns_api_urls.build_optional_urlpatterns()
    names = [pattern.name for pattern in patterns]

    assert names == [
        "return-case-document-api",
        "return-analytics-api",
        "return-case-audit-export-api",
    ]
