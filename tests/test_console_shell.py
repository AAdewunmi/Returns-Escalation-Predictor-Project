# path: tests/test_console_shell.py
"""Integration tests for ReturnHub console shell pages."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_console_renders_for_ops_user(client) -> None:
    """Ops users should see the ops console shell."""
    ops_user = UserFactory(email="console-ops@example.com")
    add_group(ops_user, "Ops")
    ReturnCaseFactory.create_batch(2, status="submitted")

    client.force_login(ops_user)
    response = client.get("/console/ops/")

    assert response.status_code == 200
    assert "Ops Console" in response.content.decode()
    assert 'aria-label="Primary"' in response.content.decode()


@pytest.mark.django_db
def test_customer_gets_403_on_ops_console(client) -> None:
    """Customers must not access the ops console."""
    customer_user = UserFactory(email="console-customer@example.com")
    add_group(customer_user, "Customer")
    CustomerProfileFactory(user=customer_user)

    client.force_login(customer_user)
    response = client.get("/console/ops/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_console_shows_customer_shell(client) -> None:
    """Customers should be able to load their own console shell."""
    customer_user = UserFactory(email="console-customer-own@example.com")
    add_group(customer_user, "Customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    ReturnCaseFactory(customer=customer_profile)

    client.force_login(customer_user)
    response = client.get("/console/customer/")

    assert response.status_code == 200
    assert "Customer Console" in response.content.decode()


@pytest.mark.django_db
def test_merchant_console_renders_for_merchant_user(client) -> None:
    """Merchants should see the merchant console shell."""
    merchant_user = UserFactory(email="console-merchant@example.com")
    add_group(merchant_user, "Merchant")
    merchant_profile = MerchantProfileFactory(user=merchant_user)
    ReturnCaseFactory(merchant=merchant_profile)

    client.force_login(merchant_user)
    response = client.get("/console/merchant/")

    assert response.status_code == 200
    assert "Merchant Console" in response.content.decode()
