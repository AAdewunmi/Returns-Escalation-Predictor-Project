# path: api/views/return_documents.py
"""
Canonical live API view for listing and uploading return-case documents.
"""

from __future__ import annotations

import hashlib

from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.serializers.return_documents import (
    ReturnDocumentSerializer,
    ReturnDocumentUploadSerializer,
)
from apps.returns.models import CaseEvent, EvidenceDocument, ReturnCase


def _user_in_group(user, group_name: str) -> bool:
    """
    Return True when the user belongs to the given role group.
    """

    return user.is_superuser or Group.objects.filter(user=user, name=group_name).exists()


def _resolve_actor_role(user) -> str:
    """
    Resolve the current workflow role for the authenticated user.
    """

    if user.is_superuser:
        return "admin"
    if _user_in_group(user, "ops"):
        return "ops"
    if _user_in_group(user, "merchant"):
        return "merchant"
    if _user_in_group(user, "customer"):
        return "customer"
    return "unknown"


def _can_view_case(user, return_case: ReturnCase) -> bool:
    """
    Determine whether the authenticated user may access the case at all.
    """

    actor_role = _resolve_actor_role(user)

    if actor_role in {"admin", "ops"}:
        return True

    if actor_role == "customer":
        return return_case.customer_profile.user_id == user.id

    if actor_role == "merchant":
        return return_case.merchant_profile.user_id == user.id

    return False


def _can_upload_document(user, return_case: ReturnCase) -> bool:
    """
    Restrict uploads on the live route to the owning customer for this sprint task.
    """

    actor_role = _resolve_actor_role(user)
    return actor_role == "customer" and return_case.customer_profile.user_id == user.id


def _visible_documents_queryset(user, return_case: ReturnCase):
    """
    Return the correct document queryset for the authenticated actor.
    """

    actor_role = _resolve_actor_role(user)
    queryset = return_case.documents.all().order_by("created_at", "id")

    if actor_role in {"admin", "ops"}:
        return queryset

    if actor_role == "customer":
        return queryset.filter(visible_to_customer=True)

    if actor_role == "merchant":
        return queryset.filter(visible_to_merchant=True)

    return queryset.none()


class ReturnDocumentsLiveView(APIView):
    """
    Serve the canonical live return-documents route.

    GET returns documents visible to the current actor.
    POST allows the owning customer to upload an evidence document and records a case event.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _get_case(self, return_id: int) -> ReturnCase:
        """
        Fetch the case and related ownership data.
        """

        return get_object_or_404(
            ReturnCase.objects.select_related(
                "customer_profile__user",
                "merchant_profile__user",
            ),
            pk=return_id,
        )

    def get(self, request, return_id: int) -> Response:
        """
        Return documents visible to the authenticated actor for the given return case.
        """

        return_case = self._get_case(return_id)

        if not _can_view_case(request.user, return_case):
            return Response(
                {"detail": "You do not have permission to view documents for this return case."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReturnDocumentSerializer(
            _visible_documents_queryset(request.user, return_case),
            many=True,
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request, return_id: int) -> Response:
        """
        Upload a customer evidence document against the given return case.
        """

        return_case = self._get_case(return_id)

        if not _can_upload_document(request.user, return_case):
            return Response(
                {"detail": "You do not have permission to upload this document for the case."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReturnDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        uploaded_bytes = uploaded_file.read()
        uploaded_file.seek(0)

        document = EvidenceDocument.objects.create(
            return_case=return_case,
            uploaded_by=request.user,
            actor_role="customer",
            kind=serializer.validated_data["kind"],
            file=uploaded_file,
            file_path="",
            original_filename=uploaded_file.name,
            content_type=getattr(uploaded_file, "content_type", "application/octet-stream"),
            byte_size=getattr(uploaded_file, "size", 0),
            checksum_sha256=hashlib.sha256(uploaded_bytes).hexdigest(),
            notes=serializer.validated_data.get("notes", ""),
            visible_to_customer=True,
            visible_to_merchant=False,
        )

        # Persist the final storage path separately because this repository keeps file_path as a field.
        if not document.file_path and document.file:
            document.file_path = document.file.name
            document.save(update_fields=["file_path"])

        CaseEvent.objects.create(
            return_case=return_case,
            event_type="document_uploaded",
            actor=request.user,
            actor_role="customer",
            payload={
                "document_id": document.id,
                "kind": document.kind,
                "original_filename": document.original_filename,
                "content_type": document.content_type,
                "byte_size": document.byte_size,
            },
        )

        response_serializer = ReturnDocumentSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
