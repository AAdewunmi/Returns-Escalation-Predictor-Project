# path: tests/test_seed_returnhub_demo.py
"""Integration tests for the deterministic demo seed command."""

import pytest
from django.core.management import call_command

from apps.returns.models import CustomerProfile, MerchantProfile, ReturnCase

pytestmark = pytest.mark.django_db


def test_seed_returnhub_demo_is_idempotent():
    """Running the seed command twice should keep stable totals."""
    call_command("seed_returnhub_demo")
    first_case_count = ReturnCase.objects.count()
    first_customer_count = CustomerProfile.objects.count()
    first_merchant_count = MerchantProfile.objects.count()

    call_command("seed_returnhub_demo")

    assert first_case_count == 32
    assert ReturnCase.objects.count() == 32
    assert CustomerProfile.objects.count() == first_customer_count == 2
    assert MerchantProfile.objects.count() == first_merchant_count == 2


def test_seed_returnhub_demo_creates_page_two_coverage():
    """Seeded data should provide enough cases for page 2 in customer and merchant portals."""
    call_command("seed_returnhub_demo")

    customer_one_cases = ReturnCase.objects.filter(customer__user__username="customer.one").count()
    merchant_one_cases = ReturnCase.objects.filter(merchant__user__username="merchant.one").count()

    assert customer_one_cases == 16
    assert merchant_one_cases == 16
