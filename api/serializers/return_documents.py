"""Serializers for the canonical live return-documents API route."""

from __future__ import annotations

from rest_framework import serializers

from returns.models import EvidenceDocument


class ReturnDocumentSerializer(serializers.ModelSerializer):
    """Serialize stored evidence metadata for the live return-documents route."""

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
        """Return the persisted file path, or the stored file name as fallback."""

        if obj.file_path:
            return obj.file_path
        if obj.file:
            return obj.file.name
        return ""


class ReturnDocumentUploadSerializer(serializers.Serializer):
    """Validate uploads for the canonical live return-documents endpoint."""

    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)
    kind = serializers.CharField(required=False, allow_blank=True, default="evidence")

    def validate_kind(self, value: str) -> str:
        """Restrict the live route to the currently supported evidence upload kind."""

        normalized = (value or EvidenceDocument.DocumentKind.EVIDENCE).strip().lower()
        if normalized != EvidenceDocument.DocumentKind.EVIDENCE:
            raise serializers.ValidationError("Only kind='evidence' is currently supported.")
        return normalized
