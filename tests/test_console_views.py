"""Tests for authenticated console routes."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from returns.models import ReturnCase
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
def test_ops_console_renders_counts_and_recent_cases(client) -> None:
    """Ops dashboard should render the current queue counts and recent cases."""
    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    submitted_case = ReturnCaseFactory(
        status=ReturnCase.Status.SUBMITTED,
        order_reference="OPS-1001",
        return_reason="Damaged item",
    )
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW, order_reference="OPS-1002")

    client.force_login(ops_user)
    response = client.get(reverse("console:ops-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert "Ops Console" in body
    assert "Submitted" in body
    assert "In review" in body
    assert submitted_case.order_reference in body


@pytest.mark.django_db
def test_customer_console_renders_only_customer_cases(client) -> None:
    """Customer dashboard should render recent cases tied to the current customer."""
    customer_profile = CustomerProfileFactory()
    add_group(customer_profile.user, "Customer")
    owned_case = ReturnCaseFactory(customer=customer_profile, order_reference="CUS-1001")
    ReturnCaseFactory(order_reference="CUS-9999")

    client.force_login(customer_profile.user)
    response = client.get(reverse("console:customer-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert owned_case.order_reference in body
    assert "CUS-9999" not in body


@pytest.mark.django_db
def test_merchant_console_renders_only_merchant_cases(client) -> None:
    """Merchant dashboard should render recent cases tied to the current merchant."""
    merchant_profile = MerchantProfileFactory()
    add_group(merchant_profile.user, "Merchant")
    owned_case = ReturnCaseFactory(merchant=merchant_profile, order_reference="MER-1001")
    ReturnCaseFactory(order_reference="MER-9999")

    client.force_login(merchant_profile.user)
    response = client.get(reverse("console:merchant-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert owned_case.order_reference in body
    assert "MER-9999" not in body


@pytest.mark.django_db
def test_console_routes_forbid_wrong_role(client) -> None:
    """Console routes should reject authenticated users without the required role."""
    customer_profile = CustomerProfileFactory()
    add_group(customer_profile.user, "Customer")

    client.force_login(customer_profile.user)
    response = client.get(reverse("console:ops-dashboard"))

    assert response.status_code == 403
