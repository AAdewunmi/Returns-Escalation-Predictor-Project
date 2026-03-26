# path: returns/api/serializers/detail.py
"""Detail serializers for return-case API responses."""

from __future__ import annotations

from rest_framework import serializers

from returns.api.permissions import is_admin, is_ops
from returns.models import ReturnCase, RiskScore


class EmbeddedRiskScoreSerializer(serializers.ModelSerializer):
    """Serialise the persisted risk payload embedded in a return-case response."""

    class Meta:
        model = RiskScore
        fields = ("model_version", "score", "label", "reason_codes", "scored_at")


class ReturnCaseDetailSerializer(serializers.ModelSerializer):
    """Detailed return-case read model aligned with the current project schema."""

    merchant_name = serializers.CharField(source="merchant.display_name", read_only=True)
    customer_email = serializers.EmailField(source="customer.user.email", read_only=True)
    risk = serializers.SerializerMethodField()

    class Meta:
        model = ReturnCase
        fields = (
            "id",
            "order_reference",
            "status",
            "priority",
            "merchant_name",
            "customer_email",
            "item_category",
            "return_reason",
            "customer_message",
            "order_value",
            "delivery_date",
            "risk",
            "created_at",
            "updated_at",
        )

    def get_risk(self, obj: ReturnCase):
        """Expose risk only to ops and admin users, matching the live API contract."""

        request = self.context.get("request")
        if request is None or not (is_ops(request.user) or is_admin(request.user)):
            return None

        risk_score = RiskScore.objects.filter(case=obj).first()
        if risk_score is None:
            return None

        return EmbeddedRiskScoreSerializer(risk_score).data
