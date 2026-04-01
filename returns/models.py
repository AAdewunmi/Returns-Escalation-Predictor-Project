"""Operational models for the ReturnHub workflow."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import CustomerProfile, MerchantProfile
from common.models import TimeStampedModel


def build_document_upload_path(instance: EvidenceDocument, filename: str) -> str:
    """Build a traceable upload path for stored evidence files."""

    extension = Path(filename).suffix.lower()
    stem = slugify(Path(filename).stem) or "document"
    created_at = instance.created_at or timezone.now()
    case_id = instance.return_case_id or "unassigned"
    document_kind = instance.kind or "document"
    suffix = instance.pk or uuid.uuid4()
    return (
        f"return-cases/{case_id}/{document_kind}/{created_at:%Y/%m}/"
        f"{stem}-{suffix.hex[:12]}{extension}"
    )


def _calculate_file_checksum(file_field) -> str:
    """Return a SHA-256 checksum for the uploaded file."""

    hasher = hashlib.sha256()
    was_open = getattr(file_field, "closed", True) is False
    position = None

    if hasattr(file_field, "tell"):
        try:
            position = file_field.tell()
        except (OSError, ValueError):
            position = None

    if not was_open:
        file_field.open("rb")

    try:
        if hasattr(file_field, "seek"):
            try:
                file_field.seek(0)
            except (OSError, ValueError):
                pass

        for chunk in file_field.chunks():
            hasher.update(chunk)
    finally:
        if position is not None and hasattr(file_field, "seek"):
            try:
                file_field.seek(position)
            except (OSError, ValueError):
                pass
        if not was_open:
            file_field.close()

    return hasher.hexdigest()


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
    file = models.FileField(upload_to=build_document_upload_path, blank=True, null=True)
    file_path = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    byte_size = models.PositiveIntegerField()
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True)
    visible_to_customer = models.BooleanField(default=True)
    visible_to_merchant = models.BooleanField(default=True)

    class Meta:
        """Meta configuration for evidence documents."""

        ordering = ["-created_at", "id"]

    def save(self, *args, **kwargs):
        """Persist uploaded file metadata into stable model fields."""

        if self.file:
            if not self.file_path:
                self.file_path = self.file.name
            if not self.original_filename:
                self.original_filename = os.path.basename(self.file.name)
            if not self.content_type:
                self.content_type = getattr(self.file, "content_type", "application/octet-stream")
            if not self.byte_size:
                self.byte_size = getattr(self.file, "size", 0)
            if not self.checksum_sha256:
                self.checksum_sha256 = _calculate_file_checksum(self.file)

        super().save(*args, **kwargs)


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


class RiskScore(TimeStampedModel):
    """Persisted placeholder ML risk output for a return case."""

    case = models.OneToOneField(
        ReturnCase,
        on_delete=models.CASCADE,
        related_name="risk_score",
    )
    model_version = models.CharField(max_length=64)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    label = models.CharField(max_length=16)
    reason_codes = models.JSONField(default=list, blank=True)
    scored_at = models.DateTimeField()

    class Meta:
        """Meta configuration for persisted risk scores."""

        ordering = ["-scored_at", "id"]
