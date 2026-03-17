# path: tests/integration/api/test_returns_api.py
"""Integration tests for ReturnHub return workflow API endpoints."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from returns.models import CaseEvent, ReturnCase
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
def test_customer_can_create_return_case_via_api() -> None:
    """Customers should be able to create cases through the API."""
    client = APIClient()
    customer_user = UserFactory(email="api-customer@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)
    merchant = MerchantProfileFactory()

    client.force_authenticate(customer_user)
    response = client.post(
        "/api/returns/",
        data={
            "merchant_id": str(merchant.pk),
            "external_order_ref": "ORDER-5001",
            "item_category": "electronics",
            "return_reason": "damaged",
            "customer_message": "The laptop hinge is snapped and cannot close properly.",
            "order_value": "799.00",
            "delivery_date": "2026-03-01",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == "submitted"
    assert CaseEvent.objects.filter(event_type="case_created").count() == 1


@pytest.mark.django_db
def test_customer_can_retrieve_only_their_own_case() -> None:
    """Customers should be able to retrieve their own cases."""
    client = APIClient()
    customer_user = UserFactory(email="api-customer-own@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    case = ReturnCaseFactory(customer=customer_profile)

    client.force_authenticate(customer_user)
    response = client.get(f"/api/returns/{case.pk}/")

    assert response.status_code == 200
    assert response.data["id"] == case.pk


@pytest.mark.django_db
def test_wrong_customer_gets_403_on_case_detail() -> None:
    """Customers must not be able to access another customer's case."""
    client = APIClient()
    customer_user = UserFactory(email="wrong-customer@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)
    case = ReturnCaseFactory()

    client.force_authenticate(customer_user)
    response = client.get(f"/api/returns/{case.pk}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_ops_can_update_status_but_customer_cannot() -> None:
    """Ops can patch status while customers are forbidden."""
    customer_client = APIClient()
    ops_client = APIClient()

    customer_user = UserFactory(email="api-customer-forbidden@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)

    ops_user = UserFactory(email="api-ops@example.com")
    add_group(ops_user, "ops")

    case = ReturnCaseFactory(status="submitted")

    customer_client.force_authenticate(customer_user)
    customer_response = customer_client.patch(
        f"/api/returns/{case.pk}/status/",
        data={"status": ReturnCase.Status.IN_REVIEW},
        format="json",
    )

    ops_client.force_authenticate(ops_user)
    ops_response = ops_client.patch(
        f"/api/returns/{case.pk}/status/",
        data={"status": ReturnCase.Status.IN_REVIEW, "priority": ReturnCase.Priority.HIGH},
        format="json",
    )

    assert customer_response.status_code == 403
    assert ops_response.status_code == 200
    assert ops_response.data["status"] == ReturnCase.Status.IN_REVIEW
    assert ops_response.data["priority"] == ReturnCase.Priority.HIGH


@pytest.mark.django_db
def test_invalid_status_transition_returns_400() -> None:
    """Invalid service-layer transitions should surface as API validation failures."""
    client = APIClient()
    ops_user = UserFactory(email="api-ops-invalid@example.com")
    add_group(ops_user, "ops")
    case = ReturnCaseFactory(status=ReturnCase.Status.APPROVED)

    client.force_authenticate(ops_user)
    response = client.patch(
        f"/api/returns/{case.pk}/status/",
        data={"status": ReturnCase.Status.IN_REVIEW},
        format="json",
    )

    assert response.status_code == 400
    assert "Invalid status transition" in response.data["detail"]


@pytest.mark.django_db
def test_ops_can_add_internal_note() -> None:
    """Ops should be able to add notes through the API."""
    client = APIClient()
    ops_user = UserFactory(email="api-ops-note@example.com")
    add_group(ops_user, "ops")
    case = ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)

    client.force_authenticate(ops_user)
    response = client.post(
        f"/api/returns/{case.pk}/notes/",
        data={"body": "Packaging photos support a likely carrier damage claim."},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["body"] == "Packaging photos support a likely carrier damage claim."
