"""Tests for account profile models."""

import pytest
from django.contrib.auth import get_user_model

from accounts.models import CustomerProfile, MerchantProfile


@pytest.mark.django_db
def test_customer_profile_string_representation():
    """CustomerProfile.__str__ should include the external reference."""
    user = get_user_model().objects.create_user(
        username="customer-user",
        password="password123",
    )
    profile = CustomerProfile.objects.create(
        user=user,
        external_reference="cust-001",
        display_name="Customer One",
    )

    assert str(profile) == "CustomerProfile<cust-001>"


@pytest.mark.django_db
def test_merchant_profile_string_representation():
    """MerchantProfile.__str__ should include the merchant code."""
    user = get_user_model().objects.create_user(
        username="merchant-user",
        password="password123",
    )
    profile = MerchantProfile.objects.create(
        user=user,
        merchant_code="mrc-001",
        display_name="Merchant One",
        support_email="support@example.com",
    )

    assert str(profile) == "MerchantProfile<mrc-001>"
