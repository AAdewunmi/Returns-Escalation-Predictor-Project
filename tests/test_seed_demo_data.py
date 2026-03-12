# path: tests/test_seed_demo_data.py
"""Integration tests for model persistence and demo seeding."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import CaseEvent, ReturnCase


def test_seed_demo_data_is_idempotent(db) -> None:
    """Running the seed command twice should keep stable record counts."""
    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Group.objects.count() == 4
    assert ReturnCase.objects.count() == 32
    assert CaseEvent.objects.count() == 32
    assert CustomerProfile.objects.count() == 1
    assert MerchantProfile.objects.count() == 1

def test_seed_demo_data_creates_expected_users_and_groups(db) -> None:
    """The demo seed should create the expected demo identities."""
    call_command("seed_demo_data")
    user_model = get_user_model()

    admin_user = user_model.objects.get(username="admin")
    ops_user = user_model.objects.get(username="ops")
    customer_user = user_model.objects.get(username="customer")
    merchant_user = user_model.objects.get(username="merchant")

    assert admin_user.is_superuser is True
    assert ops_user.groups.filter(name="Ops").exists() is True
    assert customer_user.customer_profile.external_reference == "CUS-0001"
    assert merchant_user.merchant_profile.merchant_code == "MER-0001"
