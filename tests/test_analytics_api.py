"""Integration tests for ReturnHub analytics API endpoints."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from returns.models import ReturnCase
from tests.factories import CustomerProfileFactory, ReturnCaseFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_can_fetch_return_analytics() -> None:
    """Ops users should be able to retrieve aggregated return metrics."""
    client = APIClient()
    ops_user = UserFactory(email="analytics-ops@example.com")
    add_group(ops_user, "ops")
    today = timezone.localdate()

    ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED, priority=ReturnCase.Priority.MEDIUM)
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW, priority=ReturnCase.Priority.HIGH)

    client.force_authenticate(ops_user)
    response = client.get(
        reverse("analytics-api:return-analytics"),
        data={"from": today.isoformat(), "to": today.isoformat()},
    )

    assert response.status_code == 200
    assert response.data["from"] == today.isoformat()
    assert response.data["to"] == today.isoformat()
    assert response.data["total_cases"] == 2
    assert response.data["status_counts"][ReturnCase.Status.SUBMITTED] == 1
    assert response.data["status_counts"][ReturnCase.Status.IN_REVIEW] == 1
    assert response.data["priority_counts"][ReturnCase.Priority.MEDIUM] == 1
    assert response.data["priority_counts"][ReturnCase.Priority.HIGH] == 1


@pytest.mark.django_db
def test_analytics_api_requires_ops_or_admin() -> None:
    """Customers should be forbidden from using the analytics endpoint."""
    client = APIClient()
    customer_user = UserFactory(email="analytics-customer@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)
    today = timezone.localdate()

    client.force_authenticate(customer_user)
    response = client.get(
        reverse("analytics-api:return-analytics"),
        data={"from": today.isoformat(), "to": today.isoformat()},
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_analytics_api_returns_400_for_missing_query_parameter() -> None:
    """The endpoint should require both from and to query parameters."""
    client = APIClient()
    ops_user = UserFactory(email="analytics-missing@example.com")
    add_group(ops_user, "ops")
    today = timezone.localdate()

    client.force_authenticate(ops_user)
    response = client.get(
        reverse("analytics-api:return-analytics"),
        data={"from": today.isoformat()},
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Missing required query parameter: to"


@pytest.mark.django_db
def test_analytics_api_returns_400_for_invalid_date_format() -> None:
    """The endpoint should reject non-ISO date query parameters."""
    client = APIClient()
    ops_user = UserFactory(email="analytics-format@example.com")
    add_group(ops_user, "ops")

    client.force_authenticate(ops_user)
    response = client.get(
        reverse("analytics-api:return-analytics"),
        data={"from": "03/18/2026", "to": "2026-03-18"},
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Dates must use ISO format YYYY-MM-DD."


@pytest.mark.django_db
def test_analytics_api_returns_400_for_inverted_date_window() -> None:
    """The endpoint should surface service validation errors."""
    client = APIClient()
    ops_user = UserFactory(email="analytics-window@example.com")
    add_group(ops_user, "ops")

    client.force_authenticate(ops_user)
    response = client.get(
        reverse("analytics-api:return-analytics"),
        data={"from": "2026-03-19", "to": "2026-03-18"},
    )

    assert response.status_code == 400
    assert response.data["detail"] == "'from' date must be on or before 'to' date."
