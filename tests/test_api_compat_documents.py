"""Tests for compatibility-layer document API modules."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

import api.urls as compat_api_urls
from api.serializers.documents import DocumentSerializer, DocumentUploadSerializer
from api.views.documents import ReturnCaseDocumentUploadApiView
from returns.models import EvidenceDocument
from returns.services.documents import DocumentServiceError
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


class _StubAPIView(APIView):
    """Simple placeholder API view for URL registration tests."""

    def get(self, request, *args, **kwargs):
        return Response({})


@pytest.mark.django_db
def test_document_upload_serializer_accepts_live_payload() -> None:
    """The compatibility upload serializer should validate the live payload shape."""
    serializer = DocumentUploadSerializer(
        data={
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "file": SimpleUploadedFile("photo.jpg", b"bytes", content_type="image/jpeg"),
            "notes": "Visible damage",
            "visible_to_customer": True,
            "visible_to_merchant": False,
        }
    )

    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_document_serializer_exposes_live_metadata_fields() -> None:
    """The compatibility document serializer should expose live evidence fields."""
    document = EvidenceDocumentFactory(notes="Visible damage")

    data = DocumentSerializer(document).data

    assert data["kind"] == document.kind
    assert data["file_path"] == document.file_path
    assert data["byte_size"] == document.byte_size
    assert data["notes"] == "Visible damage"
    assert data["actor_role"] == document.actor_role


@pytest.mark.django_db
def test_document_view_get_lists_documents(monkeypatch) -> None:
    """GET should return serialized documents from the live document service."""
    factory = APIRequestFactory()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    document = EvidenceDocumentFactory(return_case=return_case)

    request = factory.get("/api/returns/documents/")
    force_authenticate(request, user=actor)

    monkeypatch.setattr(
        "api.views.documents.list_documents_for_case",
        lambda **kwargs: [document],
    )

    response = ReturnCaseDocumentUploadApiView.as_view()(request, case_id=str(return_case.pk))

    assert response.status_code == 200
    assert response.data[0]["id"] == document.pk


@pytest.mark.django_db
def test_document_view_get_translates_permission_denied(monkeypatch) -> None:
    """GET should translate Django permission errors into DRF permission errors."""
    factory = APIRequestFactory()
    actor = UserFactory()
    return_case = ReturnCaseFactory()

    request = factory.get("/api/returns/documents/")
    force_authenticate(request, user=actor)

    def deny(**kwargs):
        raise DjangoPermissionDenied("Blocked")

    monkeypatch.setattr("api.views.documents.list_documents_for_case", deny)

    response = ReturnCaseDocumentUploadApiView.as_view()(request, case_id=str(return_case.pk))

    assert response.status_code == 403
    assert response.data == {"detail": "Blocked"}


@pytest.mark.django_db
def test_document_view_post_uploads_document(monkeypatch) -> None:
    """POST should validate the payload and return the uploaded document."""
    factory = APIRequestFactory()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    document = EvidenceDocumentFactory(return_case=return_case)
    uploaded_file = SimpleUploadedFile("photo.jpg", b"bytes", content_type="image/jpeg")

    request = factory.post(
        "/api/returns/documents/",
        {
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "file": uploaded_file,
            "notes": "Visible damage",
            "visible_to_customer": True,
            "visible_to_merchant": False,
        },
        format="multipart",
    )
    force_authenticate(request, user=actor)

    def fake_upload_document_for_case(*, return_case, actor, upload_input):
        assert upload_input.kind == EvidenceDocument.DocumentKind.EVIDENCE
        assert upload_input.notes == "Visible damage"
        assert upload_input.visible_to_customer is True
        assert upload_input.visible_to_merchant is False
        return document

    monkeypatch.setattr(
        "api.views.documents.upload_document_for_case",
        fake_upload_document_for_case,
    )

    response = ReturnCaseDocumentUploadApiView.as_view()(request, case_id=str(return_case.pk))

    assert response.status_code == 201
    assert response.data["id"] == document.pk


@pytest.mark.django_db
def test_document_view_post_translates_permission_denied(monkeypatch) -> None:
    """POST should translate Django permission errors into DRF permission errors."""
    factory = APIRequestFactory()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    uploaded_file = SimpleUploadedFile("photo.jpg", b"bytes", content_type="image/jpeg")

    request = factory.post(
        "/api/returns/documents/",
        {"kind": EvidenceDocument.DocumentKind.EVIDENCE, "file": uploaded_file},
        format="multipart",
    )
    force_authenticate(request, user=actor)

    def deny(**kwargs):
        raise DjangoPermissionDenied("Blocked")

    monkeypatch.setattr("api.views.documents.upload_document_for_case", deny)

    response = ReturnCaseDocumentUploadApiView.as_view()(request, case_id=str(return_case.pk))

    assert response.status_code == 403
    assert response.data == {"detail": "Blocked"}


@pytest.mark.django_db
def test_document_view_post_returns_bad_request_for_service_error(monkeypatch) -> None:
    """POST should return 400 when the document service rejects the payload."""
    factory = APIRequestFactory()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    uploaded_file = SimpleUploadedFile("photo.jpg", b"bytes", content_type="image/jpeg")

    request = factory.post(
        "/api/returns/documents/",
        {"kind": EvidenceDocument.DocumentKind.EVIDENCE, "file": uploaded_file},
        format="multipart",
    )
    force_authenticate(request, user=actor)

    def fail(**kwargs):
        raise DocumentServiceError("Invalid kind")

    monkeypatch.setattr("api.views.documents.upload_document_for_case", fail)

    response = ReturnCaseDocumentUploadApiView.as_view()(request, case_id=str(return_case.pk))

    assert response.status_code == 400
    assert response.data == {"detail": "Invalid kind"}


def test_compat_api_urls_build_optional_urlpatterns_omits_missing_views(monkeypatch) -> None:
    """Compatibility optional routes should be skipped when views are unavailable."""
    monkeypatch.setattr(compat_api_urls, "ReturnCaseDocumentUploadApiView", None)
    monkeypatch.setattr(compat_api_urls, "ReturnAnalyticsApiView", None)

    def missing_import(name: str):
        raise ImportError()

    monkeypatch.setattr(compat_api_urls, "import_module", missing_import)

    patterns = compat_api_urls.build_optional_urlpatterns()

    assert patterns == []


def test_compat_api_urls_import_fallbacks_handle_missing_optional_modules(monkeypatch) -> None:
    """Module import should tolerate missing compatibility-only optional views."""
    module_name = "api_urls_missing_optionals_test"
    module_path = Path(__file__).resolve().parents[1] / "api" / "urls.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    original_documents = sys.modules.get("api.views.documents")
    original_analytics = sys.modules.get("analytics.api.views")
    sys.modules["api.views.documents"] = None
    sys.modules["analytics.api.views"] = None

    try:
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)
        assert module.ReturnCaseDocumentUploadApiView is None
        assert module.ReturnAnalyticsApiView is None
    finally:
        if original_documents is None:
            sys.modules.pop("api.views.documents", None)
        else:
            sys.modules["api.views.documents"] = original_documents
        if original_analytics is None:
            sys.modules.pop("analytics.api.views", None)
        else:
            sys.modules["analytics.api.views"] = original_analytics


def test_compat_api_urls_build_optional_urlpatterns_includes_available_views(
    monkeypatch,
) -> None:
    """Compatibility optional routes should register available views."""
    monkeypatch.setattr(compat_api_urls, "ReturnCaseDocumentUploadApiView", _StubAPIView)
    monkeypatch.setattr(compat_api_urls, "ReturnAnalyticsApiView", _StubAPIView)
    monkeypatch.setattr(
        compat_api_urls,
        "import_module",
        lambda name: types.SimpleNamespace(ReturnCaseAuditExportApiView=_StubAPIView),
    )

    patterns = compat_api_urls.build_optional_urlpatterns()
    names = [pattern.name for pattern in patterns]

    assert names == [
        "api-return-document",
        "api-return-analytics",
        "api-return-audit-export",
    ]
