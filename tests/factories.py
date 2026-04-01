"""Factory objects used by return-domain tests."""

from __future__ import annotations

import datetime
import hashlib
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from factory.django import DjangoModelFactory

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import CaseEvent, EvidenceDocument, ReturnCase, RiskScore

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Create reusable authenticated users for tests."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class CustomerProfileFactory(DjangoModelFactory):
    """Create customer profiles for tests."""

    class Meta:
        model = CustomerProfile

    user = factory.SubFactory(UserFactory)
    external_reference = factory.Sequence(lambda n: f"CUS-{n:04d}")
    display_name = factory.Sequence(lambda n: f"Customer {n}")


class MerchantProfileFactory(DjangoModelFactory):
    """Create merchant profiles for tests."""

    class Meta:
        model = MerchantProfile

    user = factory.SubFactory(UserFactory)
    merchant_code = factory.Sequence(lambda n: f"MER-{n:04d}")
    display_name = factory.Sequence(lambda n: f"Merchant {n}")
    support_email = factory.Sequence(lambda n: f"merchant{n}@example.com")


class ReturnCaseFactory(DjangoModelFactory):
    """Create return cases with stable defaults."""

    class Meta:
        model = ReturnCase

    customer = factory.SubFactory(CustomerProfileFactory)
    merchant = factory.SubFactory(MerchantProfileFactory)
    order_reference = factory.Sequence(lambda n: f"TEST-{n:04d}")
    item_category = "apparel"
    return_reason = "Damaged item"
    customer_message = factory.Sequence(lambda n: f"Customer message {n}")
    order_value = Decimal("59.99")
    delivery_date = datetime.date(2025, 1, 10)
    status = ReturnCase.Status.SUBMITTED
    priority = ReturnCase.Priority.MEDIUM


class EvidenceDocumentFactory(DjangoModelFactory):
    """Create evidence documents with realistic metadata."""

    class Meta:
        model = EvidenceDocument

    return_case = factory.SubFactory(ReturnCaseFactory)
    kind = EvidenceDocument.DocumentKind.EVIDENCE
    uploaded_by = factory.LazyAttribute(lambda obj: obj.return_case.customer.user)
    actor_role = EvidenceDocument.ActorRole.CUSTOMER
    original_filename = "photo.jpg"
    content_type = "image/jpeg"
    byte_size = 14
    checksum_sha256 = hashlib.sha256(b"evidence-bytes").hexdigest()
    notes = "Customer uploaded a product photo."
    visible_to_customer = True
    visible_to_merchant = True
    file = factory.LazyFunction(
        lambda: SimpleUploadedFile(
            "photo.jpg",
            b"evidence-bytes",
            content_type="image/jpeg",
        )
    )
    file_path = factory.LazyAttribute(lambda obj: obj.file.name)


class CaseEventFactory(DjangoModelFactory):
    """Create case events for tests."""

    class Meta:
        model = CaseEvent

    return_case = factory.SubFactory(ReturnCaseFactory)
    event_type = "case_created"
    actor = factory.SubFactory(UserFactory)
    actor_role = "system"
    payload = factory.LazyFunction(dict)


class RiskScoreFactory(DjangoModelFactory):
    """Create persisted risk scores for tests."""

    class Meta:
        model = RiskScore

    case = factory.SubFactory(ReturnCaseFactory)
    model_version = "baseline-v1"
    score = Decimal("0.42")
    label = "medium"
    reason_codes = factory.LazyFunction(lambda: ["damaged_reason"])
    scored_at = factory.LazyFunction(timezone.now)
