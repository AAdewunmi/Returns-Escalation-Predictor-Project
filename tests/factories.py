# path: tests/factories.py
"""Factory classes for ReturnHub tests."""
import datetime
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import ReturnCase


class UserFactory(factory.django.DjangoModelFactory):
    """Create Django users for tests."""

    class Meta:
        """Factory metadata."""

        model = get_user_model()
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")

class CustomerProfileFactory(factory.django.DjangoModelFactory):
    """Create customer profiles for tests."""

    class Meta:
        """Factory metadata."""

        model = CustomerProfile

    user = factory.SubFactory(UserFactory)
    external_reference = factory.Sequence(lambda n: f"CUS-{n:04d}")
    display_name = factory.Sequence(lambda n: f"Customer {n}")

class MerchantProfileFactory(factory.django.DjangoModelFactory):
    """Create merchant profiles for tests."""

    class Meta:
        """Factory metadata."""

        model = MerchantProfile

    user = factory.SubFactory(UserFactory)
    merchant_code = factory.Sequence(lambda n: f"MER-{n:04d}")
    display_name = factory.Sequence(lambda n: f"Merchant {n}")
    support_email = factory.Sequence(lambda n: f"merchant{n}@example.com")

class ReturnCaseFactory(factory.django.DjangoModelFactory):
    """Create return cases for tests."""

    class Meta:
        """Factory metadata."""

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
