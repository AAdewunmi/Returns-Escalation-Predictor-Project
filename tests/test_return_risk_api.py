# path: tests/integration/api/test_return_risk_api.py
"""Integration tests for the ReturnHub risk API surface."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from returns.models import RiskScore
from tests.factories import CustomerProfileFactory, ReturnCaseFactory, UserFactory


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
    RiskScore.objects.create(
        case=case,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.55"),
        label="medium",
        reason_codes=[{"code": "repeat_returns"}],
        scored_at=datetime.datetime(2026, 3, 1, 10, 0, 0, tzinfo=datetime.UTC),
    )

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
    case = ReturnCaseFactory(customer=customer_profile)
    RiskScore.objects.create(
        case=case,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.80"),
        label="high",
        reason_codes=[],
        scored_at=datetime.datetime(2026, 3, 1, 10, 0, 0, tzinfo=datetime.UTC),
    )

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
    case = ReturnCaseFactory(customer=customer_profile)
    RiskScore.objects.create(
        case=case,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.80"),
        label="high",
        reason_codes=[],
        scored_at=datetime.datetime(2026, 3, 1, 10, 0, 0, tzinfo=datetime.UTC),
    )

    client.force_authenticate(customer_user)
    response = client.get(f"/api/returns/{case.pk}/")

    assert response.status_code == 200
    assert response.data["risk"] is None


@pytest.mark.django_db
def test_admin_gets_404_when_risk_detail_is_missing() -> None:
    """Admins may access the endpoint, but missing scores should return 404."""
    client = APIClient()
    admin_user = UserFactory(email="risk-api-admin@example.com", is_superuser=True)
    case = ReturnCaseFactory()

    client.force_authenticate(admin_user)
    response = client.get(f"/api/returns/{case.pk}/risk/")

    assert response.status_code == 404
