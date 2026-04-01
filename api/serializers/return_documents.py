# path: api/serializers/return_documents.py
"""
Serializers for the canonical live return-documents API route.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.returns.models import EvidenceDocument


class ReturnDocumentSerializer(serializers.ModelSerializer):
    """
    Serialize a stored evidence document using the current repository field names.
    """

    file_path = serializers.SerializerMethodField()

    class Meta:
        model = EvidenceDocument
        fields = [
            "id",
            "kind",
            "original_filename",
            "content_type",
            "byte_size",
            "checksum_sha256",
            "notes",
            "actor_role",
            "visible_to_customer",
            "visible_to_merchant",
            "file_path",
            "created_at",
        ]

    def get_file_path(self, obj: EvidenceDocument) -> str:
        """
        Return the persisted file path when present, otherwise fall back to the stored file name.
        """

        if obj.file_path:
            return obj.file_path
        if obj.file:
            return obj.file.name
        return ""


class ReturnDocumentUploadSerializer(serializers.Serializer):
    """
    Validate uploads for the canonical live return-documents endpoint.
    """

    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    kind = serializers.CharField(required=False, allow_blank=True, default="evidence")

    def validate_kind(self, value: str) -> str:
        """
        Restrict the current live endpoint to the repository's existing evidence kind.
        """

        normalised = (value or "evidence").strip().lower()
        if normalised != "evidence":
            raise serializers.ValidationError("Only kind='evidence' is currently supported.")
        return normalised
