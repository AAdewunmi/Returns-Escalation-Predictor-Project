# path: api/serializers/documents.py
"""
Serializers for evidence document endpoints.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.returns.models import EvidenceDocument, EvidenceDocumentKind


class DocumentUploadSerializer(serializers.Serializer):
    """
    Validate upload payloads for case documents.
    """

    document_kind = serializers.ChoiceField(choices=EvidenceDocumentKind.choices)
    file = serializers.FileField()
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serialise stored evidence metadata.
    """

    uploaded_by_role = serializers.CharField(read_only=True)

    class Meta:
        model = EvidenceDocument
        fields = [
            "id",
            "document_kind",
            "original_filename",
            "content_type",
            "size_bytes",
            "checksum_sha256",
            "note",
            "uploaded_by_role",
            "visible_to_customer",
            "visible_to_merchant",
            "created_at",
        ]