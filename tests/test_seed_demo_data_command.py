"""Tests for the seed_demo_data management command."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import CaseEvent, ReturnCase


@pytest.mark.django_db
def test_seed_demo_data_creates_expected_records():
    """The command should create stable demo users, profiles, cases, and events."""
    out = StringIO()

    call_command("seed_demo_data", stdout=out)

    user_model = get_user_model()
    assert Group.objects.filter(name__in=["Admin", "Ops", "Customer", "Merchant"]).count() == 4
    assert (
        user_model.objects.filter(username__in=["admin", "ops", "customer", "merchant"]).count()
        == 4
    )
    assert CustomerProfile.objects.filter(external_reference="CUS-0001").exists()
    assert MerchantProfile.objects.filter(merchant_code="MER-0001").exists()
    assert ReturnCase.objects.count() == 32
    assert CaseEvent.objects.filter(event_type="seed_case_created").count() == 32
    assert "Seed complete. Stable return case count: 32" in out.getvalue()


@pytest.mark.django_db
def test_seed_demo_data_is_idempotent():
    """Running the command twice should not duplicate stable seed records."""
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert ReturnCase.objects.count() == 32
    assert CaseEvent.objects.filter(event_type="seed_case_created").count() == 32
