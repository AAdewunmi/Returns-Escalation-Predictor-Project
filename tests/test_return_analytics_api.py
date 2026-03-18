# path: tests/test_return_analytics_api.py
"""Integration tests for ReturnHub analytics API."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from returns.models import ReturnCase
from tests.factories import CustomerProfileFactory, ReturnCaseFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_can_fetch_return_metrics() -> None:
    """Ops users should receive bounded return metrics."""
    client = APIClient()
    ops_user = UserFactory(email="analytics-ops@example.com")
    add_group(ops_user, "ops")

    ReturnCaseFactory.create_batch(3, status="submitted")
    ReturnCaseFactory.create_batch(2, status=ReturnCase.Status.IN_REVIEW)

    client.force_authenticate(ops_user)
    response = client.get("/api/analytics/returns/?from=2026-03-01&to=2026-03-31")

    assert response.status_code == 200
    assert response.data["total_cases"] >= 5
    assert "submitted" in response.data["status_counts"]


@pytest.mark.django_db
def test_customer_cannot_fetch_return_metrics() -> None:
    """Customers must not see ops analytics."""
    client = APIClient()
    customer_user = UserFactory(email="analytics-customer@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)

    client.force_authenticate(customer_user)
    response = client.get("/api/analytics/returns/?from=2026-03-01&to=2026-03-31")

    assert response.status_code == 403
