# path: api/views/documents.py
"""
API views for listing and uploading case documents.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.serializers.documents import DocumentSerializer, DocumentUploadSerializer
from apps.returns.models import ReturnCase
from apps.returns.services.documents import (
    DocumentUploadInput,
    list_documents_for_case,
    upload_document_for_case,
)


class ReturnDocumentView(APIView):
    """
    Provide GET and POST behaviour for case-linked documents.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_case(self, case_id):
        """
        Fetch the case for the route parameter.
        """

        return get_object_or_404(ReturnCase, id=case_id)

    def get(self, request, case_id):
        """
        List documents visible to the authenticated actor.
        """

        return_case = self.get_case(case_id)

        try:
            documents = list_documents_for_case(return_case, request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, case_id):
        """
        Upload a document for the case.
        """

        return_case = self.get_case(case_id)
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            document = upload_document_for_case(
                return_case=return_case,
                actor=request.user,
                upload_input=DocumentUploadInput(
                    document_kind=serializer.validated_data["document_kind"],
                    uploaded_file=serializer.validated_data["file"],
                    note=serializer.validated_data.get("note", ""),
                ),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)