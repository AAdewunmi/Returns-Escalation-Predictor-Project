"""Canonical live API view for listing and uploading return-case documents."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.return_documents import (
    ReturnDocumentSerializer,
    ReturnDocumentUploadSerializer,
)
from returns.models import ReturnCase
from returns.services.documents import (
    DocumentServiceError,
    DocumentUploadInput,
    list_documents_for_case,
    upload_document_for_case,
)


class ReturnDocumentsLiveView(APIView):
    """Serve the canonical live return-documents route."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_case(self, return_id: int) -> ReturnCase:
        """Fetch the case for the supplied live route identifier."""

        return get_object_or_404(ReturnCase, pk=return_id)

    def get(self, request, return_id: int) -> Response:
        """Return documents visible to the authenticated actor for the case."""

        return_case = self._get_case(return_id)

        try:
            documents = list_documents_for_case(return_case=return_case, actor=request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        serializer = ReturnDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, return_id: int) -> Response:
        """Upload a customer evidence document against the given return case."""

        return_case = self._get_case(return_id)
        serializer = ReturnDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = upload_document_for_case(
                return_case=return_case,
                actor=request.user,
                upload_input=DocumentUploadInput(
                    kind=serializer.validated_data["kind"],
                    uploaded_file=serializer.validated_data["file"],
                    notes=serializer.validated_data.get("notes", ""),
                ),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DocumentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ReturnDocumentSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
