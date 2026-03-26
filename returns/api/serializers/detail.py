# path: returns/api/serializers/detail.py
"""Detail serializers for return-case API responses."""

from __future__ import annotations

from rest_framework import serializers

from apps.returns.models import ReturnCase


class EmbeddedRiskScoreSerializer(serializers.Serializer):
    """Serialise the latest risk score embedded in a return-case response."""

    model_version = serializers.CharField()
    score = serializers.DecimalField(max_digits=6, decimal_places=4)
    label = serializers.CharField()
    reason_codes = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()


class ReturnCaseDetailSerializer(serializers.ModelSerializer):
    """Detailed return-case read model with the latest embedded risk."""

    customer_name = serializers.SerializerMethodField()
    merchant_name = serializers.SerializerMethodField()
    risk = serializers.SerializerMethodField()

    class Meta:
        model = ReturnCase
        fields = [
            "id",
            "public_case_reference",
            "order_number",
            "status",
            "priority",
            "item_category",
            "return_reason",
            "customer_message",
            "order_value",
            "delivered_at",
            "created_at",
            "first_response_due_at",
            "resolution_due_at",
            "customer_name",
            "merchant_name",
            "risk",
        ]

    def get_customer_name(self, obj: ReturnCase) -> str:
        """Return the customer display name or email."""

        full_name = obj.customer.user.get_full_name().strip()
        return full_name or obj.customer.user.email

    def get_merchant_name(self, obj: ReturnCase) -> str:
        """Return the merchant display name."""

        display_name = getattr(obj.merchant, "display_name", "") or getattr(obj.merchant, "name", "")
        if display_name:
            return display_name

        merchant_user = getattr(obj.merchant, "user", None)
        if merchant_user is None:
            return "Unknown merchant"

        full_name = merchant_user.get_full_name().strip()
        return full_name or merchant_user.email

    def get_risk(self, obj: ReturnCase):
        """Return the latest risk score as an embedded object."""

        try:
            latest_risk = obj.risk_scores.order_by("-created_at").first()
        except AttributeError:
            latest_risk = obj.riskscore_set.order_by("-created_at").first()

        if latest_risk is None:
            return None

        return EmbeddedRiskScoreSerializer(latest_risk).data
