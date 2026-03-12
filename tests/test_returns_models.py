"""Tests for returns domain models."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import ReturnCase


@pytest.mark.django_db
def test_return_case_string_representation():
    """ReturnCase.__str__ should include the order reference."""
    customer_user = get_user_model().objects.create_user(
        username="customer-for-return",
        password="password123",
    )
    merchant_user = get_user_model().objects.create_user(
        username="merchant-for-return",
        password="password123",
    )
    customer = CustomerProfile.objects.create(
        user=customer_user,
        external_reference="cust-ret-001",
        display_name="Customer Return",
    )
    merchant = MerchantProfile.objects.create(
        user=merchant_user,
        merchant_code="mrc-ret-001",
        display_name="Merchant Return",
        support_email="merchant-return@example.com",
    )
    case = ReturnCase.objects.create(
        customer=customer,
        merchant=merchant,
        order_reference="ORD-RET-001",
        item_category="Electronics",
        return_reason="Damaged",
        customer_message="Box arrived broken.",
        order_value=Decimal("149.99"),
        delivery_date=date(2026, 3, 1),
    )

    assert str(case) == "ReturnCase<ORD-RET-001>"
