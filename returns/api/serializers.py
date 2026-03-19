# path: returns/api/serializers.py
"""DRF serializers for the ReturnHub return workflow."""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from accounts.models import MerchantProfile
from returns.api.permissions import is_admin, is_ops
from returns.models import CaseNote, ReturnCase, RiskScore
from returns.services.cases import (
    ReturnCaseCreateInput,
    StatusUpdateInput,
    add_case_note,
    create_return_case,
)


class ReturnCaseCreateSerializer(serializers.Serializer):
    """Validate and create a new return case through the service layer."""

    merchant_id = serializers.PrimaryKeyRelatedField(
        queryset=MerchantProfile.objects.all(),
        source="merchant_profile",
    )
    external_order_ref = serializers.CharField(max_length=64)
    item_category = serializers.CharField(max_length=64)
    return_reason = serializers.CharField(max_length=64)
    customer_message = serializers.CharField(max_length=2000, allow_blank=True)
    order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    delivery_date = serializers.DateField()

    def validate_order_value(self, value: Decimal) -> Decimal:
        """Require a positive order value."""
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Order value must be greater than zero.")
        return value

    def validate_delivery_date(self, value):
        """Prevent future delivery dates."""
        if value > timezone.localdate():
            raise serializers.ValidationError("Delivery date cannot be in the future.")
        return value

    def validate_customer_message(self, value: str) -> str:
        """Require a non-empty customer message after trimming whitespace."""
        if not value.strip():
            raise serializers.ValidationError("Customer message cannot be empty.")
        return value

    def create(self, validated_data: dict) -> ReturnCase:
        """Create the case using the authenticated customer as the actor."""
        request = self.context["request"]
        return create_return_case(
            actor=request.user,
            input_data=ReturnCaseCreateInput(**validated_data),
        )


class ReturnCaseStatusUpdateSerializer(serializers.Serializer):
    """Validate payloads for status updates."""

    status = serializers.ChoiceField(
        choices=ReturnCase.Status.values,
    )
    priority = serializers.ChoiceField(
        choices=ReturnCase.Priority.values,
        required=False,
        allow_null=True,
    )

    def to_service_input(self) -> StatusUpdateInput:
        """Convert serializer data into a structured service input object."""
        return StatusUpdateInput(**self.validated_data)


class CaseNoteCreateSerializer(serializers.Serializer):
    """Validate payloads for ops note creation."""

    body = serializers.CharField(max_length=4000, allow_blank=True)

    def validate_body(self, value: str) -> str:
        """Require a non-empty note body."""
        if not value.strip():
            raise serializers.ValidationError("Note body cannot be empty.")
        return value

    def create_note(self, *, actor, case: ReturnCase) -> CaseNote:
        """Create a note for the supplied case using the validated payload."""
        return add_case_note(actor=actor, case=case, body=self.validated_data["body"])


class CaseNoteSerializer(serializers.ModelSerializer):
    """Serialise case notes for API responses."""

    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = CaseNote
        fields = ("id", "body", "author_email", "created_at")


class RiskScoreSerializer(serializers.ModelSerializer):
    """Serialise persisted risk output for ops users."""

    class Meta:
        model = RiskScore
        fields = ("model_version", "score", "label", "reason_codes", "scored_at")


class ReturnCaseDetailSerializer(serializers.ModelSerializer):
    """Serialise the canonical case detail response."""

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
        """Expose risk only to ops and admin users."""
        request = self.context.get("request")
        if request is None or not (is_ops(request.user) or is_admin(request.user)):
            return None

        risk_score = RiskScore.objects.filter(case=obj).first()
        if risk_score is None:
            return None

        return RiskScoreSerializer(risk_score).data

    def create_note(self, *, actor, case: ReturnCase) -> CaseNote:
        """Delegate note creation for compatibility with existing callers."""
        return add_case_note(actor=actor, case=case, body=self.validated_data["body"])
