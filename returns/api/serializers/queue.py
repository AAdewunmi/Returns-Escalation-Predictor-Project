# path: apps/returns/api/serializers/queue.py
"""Serializers for the ops queue API."""

from __future__ import annotations

from rest_framework import serializers

from returns.models import ReturnCase


class OpsQueueItemSerializer(serializers.ModelSerializer):
    """Serialise return-case queue items for the ops queue API."""

    customer_name = serializers.SerializerMethodField()
    merchant_name = serializers.SerializerMethodField()
    current_risk_score = serializers.DecimalField(
        max_digits=6,
        decimal_places=4,
        read_only=True,
        allow_null=True,
    )
    current_risk_label = serializers.CharField(read_only=True, allow_null=True)

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
            "created_at",
            "first_response_due_at",
            "resolution_due_at",
            "customer_name",
            "merchant_name",
            "current_risk_score",
            "current_risk_label",
        ]

    def get_customer_name(self, obj: ReturnCase) -> str:
        """Return a stable customer display value."""

        full_name = obj.customer.user.get_full_name().strip()
        return full_name or obj.customer.user.email

    def get_merchant_name(self, obj: ReturnCase) -> str:
        """Return a stable merchant display value."""

        display_name = getattr(obj.merchant, "display_name", "") or getattr(obj.merchant, "name", "")
        if display_name:
            return display_name

        merchant_user = getattr(obj.merchant, "user", None)
        if merchant_user is None:
            return "Unknown merchant"

        full_name = merchant_user.get_full_name().strip()
        return full_name or merchant_user.email
