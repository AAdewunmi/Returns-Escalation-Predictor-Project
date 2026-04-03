# path: apps/api/serializers/returns.py
"""
Serializers for return-case API projections.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.api.serializers.documents import DocumentSerializer
from apps.returns.models import ReturnCase, RiskScore


class RiskSummarySerializer(serializers.ModelSerializer):
    """
    Serialise the latest persisted risk score.
    """

    class Meta:
        model = RiskScore
        fields = [
            "model_version",
            "feature_contract_version",
            "score",
            "label",
            "reason_codes",
            "created_at",
        ]


class ReturnCaseDetailSerializer(serializers.ModelSerializer):
    """
    Serialise a return case with evidence and latest risk.
    """

    documents = serializers.SerializerMethodField()
    latest_risk = serializers.SerializerMethodField()

    class Meta:
        model = ReturnCase
        fields = [
            "id",
            "reference",
            "status",
            "priority",
            "item_category",
            "return_reason",
            "order_value_gbp",
            "customer_message",
            "prior_returns_count",
            "delivered_at",
            "opened_at",
            "sla_due_at",
            "created_at",
            "updated_at",
            "documents",
            "latest_risk",
        ]

    def get_documents(self, obj):
        """
        Serialise related documents in created order.
        """

        return DocumentSerializer(obj.documents.all(), many=True).data

    def get_latest_risk(self, obj):
        """
        Serialise the most recent risk score when it exists.
        """

        latest_risk = obj.risk_scores.first()
        if latest_risk is None:
            return None
        return RiskSummarySerializer(latest_risk).data
