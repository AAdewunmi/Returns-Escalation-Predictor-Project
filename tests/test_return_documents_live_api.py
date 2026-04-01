"""DB-backed regression tests for the canonical live return-documents route."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from api.serializers.return_documents import (
    ReturnDocumentSerializer,
    ReturnDocumentUploadSerializer,
)
from api.views.return_documents import ReturnDocumentsLiveView
from returns.models import CaseEvent, EvidenceDocument
from returns.services.documents import DocumentServiceError
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, UserFactory


def _ensure_group(name: str) -> Group:
    """Create the group if missing and return it."""

    group, _ = Group.objects.get_or_create(name=name)
    return group


def test_return_document_serializer_uses_fallback_file_name_when_file_path_missing() -> None:
    """The serializer should fall back to the stored file name when file_path is blank."""

    document = EvidenceDocumentFactory.build(
        file_path="",
        file=SimpleUploadedFile("fallback.jpg", b"abcde", content_type="image/jpeg"),
    )

    serializer = ReturnDocumentSerializer(document)

    assert serializer.data["file_path"] == document.file.name


def test_return_document_serializer_returns_empty_path_without_file_or_file_path() -> None:
    """The serializer should emit an empty path when no persisted location exists."""

    document = EvidenceDocumentFactory.build(file_path="", file="")

    serializer = ReturnDocumentSerializer(document)

    assert serializer.data["file_path"] == ""


def test_return_document_upload_serializer_rejects_unsupported_kind() -> None:
    """The live route currently supports evidence uploads only."""

    serializer = ReturnDocumentUploadSerializer(
        data={
            "kind": "response",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
        }
    )

    assert not serializer.is_valid()
    assert serializer.errors["kind"] == ["Only kind='evidence' is currently supported."]


@pytest.mark.django_db
def test_live_view_get_translates_service_permission_denial(monkeypatch) -> None:
    """The live view should convert domain permission denial into DRF permission denial."""

    request = APIRequestFactory().get("/returns/1/documents/")
    force_authenticate(request, user=UserFactory())
    return_case = ReturnCaseFactory()

    monkeypatch.setattr(ReturnDocumentsLiveView, "_get_case", lambda self, return_id: return_case)

    def deny(**kwargs):
        raise DjangoPermissionDenied("Forbidden list")

    monkeypatch.setattr("api.views.return_documents.list_documents_for_case", deny)

    response = ReturnDocumentsLiveView.as_view()(request, return_id=return_case.pk)

    assert response.status_code == 403
    assert response.data == {"detail": "Forbidden list"}


@pytest.mark.django_db
def test_live_view_post_returns_400_for_service_error(monkeypatch) -> None:
    """The live view should surface document service workflow errors as 400 responses."""

    request = APIRequestFactory().post(
        "/returns/1/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Visible damage",
        },
        format="multipart",
    )
    force_authenticate(request, user=UserFactory())
    return_case = ReturnCaseFactory()

    monkeypatch.setattr(ReturnDocumentsLiveView, "_get_case", lambda self, return_id: return_case)
    monkeypatch.setattr(
        "api.views.return_documents.upload_document_for_case",
        lambda **kwargs: (_ for _ in ()).throw(DocumentServiceError("Bad upload")),
    )

    response = ReturnDocumentsLiveView.as_view()(request, return_id=return_case.pk)

    assert response.status_code == 400
    assert response.data == {"detail": "Bad upload"}


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="api.urls", ALLOWED_HOSTS=["testserver", "localhost"])
def test_live_get_returns_200_for_case_customer_and_omits_hidden_documents() -> None:
    """The owning customer should see only customer-visible documents."""

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")
    customer_user = return_case.customer.user
    customer_group.user_set.add(customer_user)

    visible_document = EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=customer_user,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
        original_filename="seed-photo.jpg",
        visible_to_customer=True,
        visible_to_merchant=True,
    )
    hidden_document = EvidenceDocumentFactory(
        return_case=return_case,
        uploaded_by=UserFactory(),
        actor_role=EvidenceDocument.ActorRole.OPS,
        kind=EvidenceDocument.DocumentKind.RESPONSE,
        original_filename="ops-internal.txt",
        visible_to_customer=False,
        visible_to_merchant=False,
    )

    client.force_authenticate(user=customer_user)
    response = client.get(f"/returns/{return_case.pk}/documents/")

    assert response.status_code == 200
    returned_filenames = [item["original_filename"] for item in response.data]
    assert visible_document.original_filename in returned_filenames
    assert hidden_document.original_filename not in returned_filenames


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="api.urls", ALLOWED_HOSTS=["testserver", "localhost"])
def test_live_post_returns_201_with_metadata_and_creates_document_uploaded_event(
    monkeypatch,
) -> None:
    """The owning customer should be able to upload a JPG and receive metadata."""

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")
    customer_user = return_case.customer.user
    customer_group.user_set.add(customer_user)

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_authenticate(user=customer_user)
    response = client.post(
        f"/returns/{return_case.pk}/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Visible damage",
        },
        format="multipart",
    )

    assert response.status_code == 201
    assert response.data["kind"] == "evidence"
    assert response.data["original_filename"] == "photo.jpg"
    assert response.data["content_type"] == "image/jpeg"
    assert response.data["byte_size"] == 5
    assert response.data["notes"] == "Visible damage"
    assert response.data["actor_role"] == "customer"
    assert response.data["visible_to_customer"] is True
    assert response.data["visible_to_merchant"] is False
    assert response.data["file_path"].startswith(f"return-cases/{return_case.pk}/evidence/")

    assert CaseEvent.objects.filter(
        return_case=return_case,
        event_type="document_uploaded",
    ).exists()


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="api.urls", ALLOWED_HOSTS=["testserver", "localhost"])
def test_live_post_returns_403_for_wrong_customer() -> None:
    """A different customer must not upload against another customer's case."""

    client = APIClient()
    return_case = ReturnCaseFactory()

    customer_group = _ensure_group("customer")
    wrong_customer = UserFactory(username="wrong-customer-live-docs")
    customer_group.user_set.add(wrong_customer)

    client.force_authenticate(user=wrong_customer)
    response = client.post(
        f"/returns/{return_case.pk}/documents/",
        {
            "kind": "evidence",
            "file": SimpleUploadedFile("photo.jpg", b"abcde", content_type="image/jpeg"),
            "notes": "Should be forbidden",
        },
        format="multipart",
    )

    assert response.status_code == 403
    assert response.data["detail"] == "Customers can only upload evidence to their own cases."
