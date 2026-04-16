"""Tests for the seed_returnhub_demo management command."""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import ReturnCase


@pytest.mark.django_db
def test_seed_returnhub_demo_creates_expected_records() -> None:
    """The command should create stable multi-surface users, profiles, and cases."""

    out = StringIO()

    call_command("seed_returnhub_demo", stdout=out)

    user_model = get_user_model()
    assert Group.objects.filter(name__in=["admin", "ops", "customer", "merchant"]).count() == 4
    assert (
        user_model.objects.filter(
            username__in=[
                "admin.demo",
                "ops.demo",
                "customer.one",
                "customer.two",
                "merchant.one",
                "merchant.two",
            ]
        ).count()
        == 6
    )
    assert CustomerProfile.objects.filter(external_reference="CUS-DEMO-0001").exists()
    assert CustomerProfile.objects.filter(external_reference="CUS-DEMO-0002").exists()
    assert MerchantProfile.objects.filter(merchant_code="MER-DEMO-0001").exists()
    assert MerchantProfile.objects.filter(merchant_code="MER-DEMO-0002").exists()
    assert ReturnCase.objects.filter(order_reference__startswith="RH-").count() == 32
    assert "ReturnHub demo seed complete." in out.getvalue()
    assert "Customer users: customer.one, customer.two" in out.getvalue()
    assert "Merchant users: merchant.one, merchant.two" in out.getvalue()


@pytest.mark.django_db
def test_seed_returnhub_demo_is_idempotent() -> None:
    """Running the command twice should keep deterministic demo counts stable."""

    call_command("seed_returnhub_demo")
    call_command("seed_returnhub_demo")

    assert CustomerProfile.objects.filter(
        external_reference__in=["CUS-DEMO-0001", "CUS-DEMO-0002"]
    ).count() == 2
    assert MerchantProfile.objects.filter(
        merchant_code__in=["MER-DEMO-0001", "MER-DEMO-0002"]
    ).count() == 2
    assert ReturnCase.objects.filter(order_reference__startswith="RH-").count() == 32


@pytest.mark.django_db
def test_seed_returnhub_demo_reconciles_conflicting_profile_identifiers() -> None:
    """The command should recover when demo identifiers are already attached elsewhere."""

    user_model = get_user_model()

    customer_two_user = user_model.objects.create_user(
        username="customer.two",
        email="customer.two@example.com",
        password="pass-12345",
    )
    CustomerProfile.objects.create(
        user=customer_two_user,
        external_reference="CUS-LEGACY-0002",
        display_name="Legacy Customer Two",
    )

    legacy_customer_user = user_model.objects.create_user(
        username="legacy.customer",
        email="legacy.customer@example.com",
        password="pass-12345",
    )
    CustomerProfile.objects.create(
        user=legacy_customer_user,
        external_reference="CUS-DEMO-0002",
        display_name="Legacy Customer",
    )

    merchant_one_user = user_model.objects.create_user(
        username="merchant.one",
        email="merchant.one@example.com",
        password="pass-12345",
    )
    MerchantProfile.objects.create(
        user=merchant_one_user,
        merchant_code="MER-LEGACY-0001",
        display_name="Legacy Merchant One",
        support_email="legacy.merchant.one@example.com",
    )

    legacy_merchant_user = user_model.objects.create_user(
        username="legacy.merchant",
        email="legacy.merchant@example.com",
        password="pass-12345",
    )
    CustomerProfile.objects.create(
        user=user_model.objects.create_user(
            username="legacy.customer.two",
            email="legacy.customer.two@example.com",
            password="pass-12345",
        ),
        external_reference="CUS-LEGACY-0003",
        display_name="Legacy Customer Two",
    )
    MerchantProfile.objects.create(
        user=legacy_merchant_user,
        merchant_code="MER-DEMO-0001",
        display_name="Legacy Merchant",
        support_email="legacy.merchant@example.com",
    )

    call_command("seed_returnhub_demo")

    canonical_customer = CustomerProfile.objects.get(external_reference="CUS-DEMO-0002")
    canonical_merchant = MerchantProfile.objects.get(merchant_code="MER-DEMO-0001")

    assert canonical_customer.user.username == "customer.two"
    assert canonical_merchant.user.username == "merchant.one"
    assert CustomerProfile.objects.filter(external_reference__startswith="legacy-cus-").exists()
    assert MerchantProfile.objects.filter(merchant_code__startswith="legacy-mer-").exists()
