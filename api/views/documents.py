"""API views for listing and uploading case documents."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers.documents import DocumentSerializer, DocumentUploadSerializer
from returns.models import ReturnCase
from returns.services.documents import (
    DocumentServiceError,
    DocumentUploadInput,
    list_documents_for_case,
    upload_document_for_case,
)


class ReturnCaseDocumentUploadApiView(APIView):
    """Provide GET and POST behavior for case-linked documents."""

    permission_classes = [permissions.IsAuthenticated]

    def get_case(self, case_id: str) -> ReturnCase:
        """Fetch the case for the route parameter."""

        return get_object_or_404(ReturnCase, pk=case_id)

    def get(self, request, case_id: str):
        """List documents visible to the authenticated actor."""

        return_case = self.get_case(case_id)

        try:
            documents = list_documents_for_case(return_case=return_case, actor=request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, case_id: str):
        """Upload a document for the case."""

        return_case = self.get_case(case_id)
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = upload_document_for_case(
                return_case=return_case,
                actor=request.user,
                upload_input=DocumentUploadInput(
                    kind=serializer.validated_data["kind"],
                    uploaded_file=serializer.validated_data["file"],
                    notes=serializer.validated_data.get("notes", ""),
                    visible_to_customer=serializer.validated_data.get("visible_to_customer"),
                    visible_to_merchant=serializer.validated_data.get("visible_to_merchant"),
                ),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DocumentServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)
