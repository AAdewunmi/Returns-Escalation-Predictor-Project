"""Serializers for evidence document endpoints."""

from __future__ import annotations

from rest_framework import serializers

from returns.models import EvidenceDocument


class DocumentUploadSerializer(serializers.Serializer):
    """Validate upload payloads for case documents."""

    kind = serializers.ChoiceField(choices=EvidenceDocument.DocumentKind.choices)
    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)
    visible_to_customer = serializers.BooleanField(required=False)
    visible_to_merchant = serializers.BooleanField(required=False)


class DocumentSerializer(serializers.ModelSerializer):
    """Serialise stored evidence metadata."""

    class Meta:
        model = EvidenceDocument
        fields = [
            "id",
            "kind",
            "file_path",
            "original_filename",
            "content_type",
            "byte_size",
            "checksum_sha256",
            "notes",
            "actor_role",
            "visible_to_customer",
            "visible_to_merchant",
            "created_at",
        ]
