# path: returns/models.py
"""Operational models for the ReturnHub workflow."""
from django.conf import settings
from django.db import models

from accounts.models import CustomerProfile, MerchantProfile
from common.models import TimeStampedModel


class ReturnCase(TimeStampedModel):
    """Represents a return case tracked through the operational workflow."""

    class Status(models.TextChoices):
        """Supported return-case states for the v1 workflow."""

        SUBMITTED = "submitted", "Submitted"
        IN_REVIEW = "in_review", "In review"
        WAITING_CUSTOMER = "waiting_customer", "Waiting for customer"
        WAITING_MERCHANT = "waiting_merchant", "Waiting for merchant"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class Priority(models.TextChoices):
        """Supported operational priority values."""

        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="return_cases",
    )
    merchant = models.ForeignKey(
        MerchantProfile,
        on_delete=models.PROTECT,
        related_name="return_cases",
    )
    order_reference = models.CharField(max_length=64, unique=True)
    item_category = models.CharField(max_length=80)
    return_reason = models.CharField(max_length=120)
    customer_message = models.TextField(blank=True)
    order_value = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_date = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.SUBMITTED,
    )
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    sla_due_at = models.DateTimeField(null=True, blank=True)
    last_status_changed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Meta configuration for return cases."""

        ordering = ["-created_at", "id"]

    def __str__(self) -> str:
        """Return a readable representation for the admin and shell."""
        return f"ReturnCase<{self.order_reference}>"


class EvidenceDocument(TimeStampedModel):
    """Represents an uploaded document associated with a return case."""

    class ActorRole(models.TextChoices):
        """Roles that can upload documents in the workflow."""

        CUSTOMER = "customer", "Customer"
        MERCHANT = "merchant", "Merchant"
        OPS = "ops", "Ops"
        ADMIN = "admin", "Admin"

    class DocumentKind(models.TextChoices):
        """Document categories used in the v1 workflow."""

        EVIDENCE = "evidence", "Evidence"
        RESPONSE = "response", "Response"

    return_case = models.ForeignKey(
        ReturnCase,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_documents",
    )
    actor_role = models.CharField(max_length=16, choices=ActorRole.choices)
    kind = models.CharField(max_length=16, choices=DocumentKind.choices)
    file_path = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField()
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        """Meta configuration for evidence documents."""

        ordering = ["-created_at", "id"]


class CaseNote(TimeStampedModel):
    """Represents an operational note attached to a return case."""

    return_case = models.ForeignKey(
        ReturnCase,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="case_notes",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=True)

    class Meta:
        """Meta configuration for case notes."""

        ordering = ["-created_at", "id"]


class CaseEvent(TimeStampedModel):
    """Append-only audit event for key workflow actions."""

    return_case = models.ForeignKey(
        ReturnCase,
        on_delete=models.CASCADE,
        related_name="events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="case_events",
        null=True,
        blank=True,
    )
    actor_role = models.CharField(max_length=16, blank=True)
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        """Meta configuration for case events."""

        ordering = ["created_at", "id"]
