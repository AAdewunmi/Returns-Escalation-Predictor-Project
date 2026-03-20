# path: tests/integration/api/test_return_risk_api.py
"""Integration tests for the ReturnHub risk API surface."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from tests.factories.accounts import CustomerProfileFactory, UserFactory
from tests.factories.returns import ReturnCaseFactory, RiskScoreFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_can_fetch_risk_detail() -> None:
    """Ops users should be able to access the dedicated risk endpoint."""
    client = APIClient()
    ops_user = UserFactory(email="risk-api-ops@example.com")
    add_group(ops_user, "ops")
    case = ReturnCaseFactory()
    RiskScoreFactory(case=case, label="medium")

    client.force_authenticate(ops_user)
    response = client.get(f"/api/returns/{case.pk}/risk/")

    assert response.status_code == 200
    assert response.data["label"] == "medium"
    assert "reason_codes" in response.data


@pytest.mark.django_db
def test_customer_cannot_fetch_risk_detail() -> None:
    """Customers must not access the dedicated risk endpoint."""
    client = APIClient()
    customer_user = UserFactory(email="risk-api-customer@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    case = ReturnCaseFactory(customer_profile=customer_profile)
    RiskScoreFactory(case=case, label="high")

    client.force_authenticate(customer_user)
    response = client.get(f"/api/returns/{case.pk}/risk/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_detail_response_hides_risk_payload() -> None:
    """Customer-facing detail should not expose risk even when a score exists."""
    client = APIClient()
    customer_user = UserFactory(email="risk-hidden-customer@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    case = ReturnCaseFactory(customer_profile=customer_profile)
    RiskScoreFactory(case=case, label="high")

    client.force_authenticate(customer_user)
    response = client.get(f"/api/returns/{case.pk}/")

    assert response.status_code == 200
    assert response.data["risk"] is None
