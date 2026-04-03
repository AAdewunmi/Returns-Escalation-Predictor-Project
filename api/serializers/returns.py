# path: api/serializers/returns.py
"""Serializers for return-case API projections."""

from __future__ import annotations

from rest_framework import serializers

from api.serializers.documents import DocumentSerializer
from returns.models import ReturnCase, RiskScore


class RiskSummarySerializer(serializers.ModelSerializer):
    """Serialise the latest persisted risk score."""

    class Meta:
        model = RiskScore
        fields = [
            "model_version",
            "score",
            "label",
            "reason_codes",
            "scored_at",
            "created_at",
        ]


class ReturnCaseDetailSerializer(serializers.ModelSerializer):
    """Serialise a return case with evidence documents and the latest risk score."""

    documents = serializers.SerializerMethodField()
    latest_risk = serializers.SerializerMethodField()

    class Meta:
        model = ReturnCase
        fields = [
            "id",
            "order_reference",
            "status",
            "priority",
            "item_category",
            "return_reason",
            "order_value",
            "customer_message",
            "delivery_date",
            "sla_due_at",
            "last_status_changed_at",
            "created_at",
            "updated_at",
            "documents",
            "latest_risk",
        ]

    def get_documents(self, obj: ReturnCase) -> list[dict]:
        """Serialise related documents in descending created order."""

        documents = obj.documents.order_by("-created_at", "-id")
        return DocumentSerializer(documents, many=True).data

    def get_latest_risk(self, obj: ReturnCase) -> dict | None:
        """Serialise the one-to-one risk score when it exists."""

        latest_risk = getattr(obj, "risk_score", None)
        if latest_risk is None:
            return None
        return RiskSummarySerializer(latest_risk).data
