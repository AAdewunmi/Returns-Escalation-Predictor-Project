"""Tests for returns API views."""

import json

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from returns.services.cases import ReturnCaseWorkflowError
from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


def _add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_return_case_create_api_creates_case_for_customer() -> None:
    """Authenticated customers should be able to create return cases."""
    client = Client()
    customer_profile = CustomerProfileFactory()
    _add_group(customer_profile.user, "Customer")
    merchant_profile = MerchantProfileFactory()
    client.force_login(customer_profile.user)

    response = client.post(
        "/api/returns/",
        data={
            "merchant_id": merchant_profile.pk,
            "external_order_ref": "ORD-5001",
            "item_category": "apparel",
            "return_reason": "damaged",
            "customer_message": "Sleeve torn on arrival.",
            "order_value": "44.50",
            "delivery_date": "2025-01-10",
        },
    )

    assert response.status_code == 201
    assert response.json()["order_reference"] == "ORD-5001"


@pytest.mark.django_db
def test_return_case_detail_api_rejects_unauthorized_case_access() -> None:
    """Customers should not be able to view another customer's case."""
    client = Client()
    actor_profile = CustomerProfileFactory()
    _add_group(actor_profile.user, "Customer")
    other_case = ReturnCaseFactory()
    client.force_login(actor_profile.user)

    response = client.get(f"/api/returns/{other_case.pk}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_return_case_detail_api_returns_case_for_authorized_customer() -> None:
    """The owning customer should be able to retrieve case detail."""
    client = Client()
    customer_profile = CustomerProfileFactory()
    _add_group(customer_profile.user, "Customer")
    case = ReturnCaseFactory(customer=customer_profile)
    client.force_login(customer_profile.user)

    response = client.get(f"/api/returns/{case.pk}/")

    assert response.status_code == 200
    assert response.json()["order_reference"] == case.order_reference


@pytest.mark.django_db
def test_return_case_status_api_returns_workflow_error(monkeypatch) -> None:
    """Workflow service errors should return a 400 response."""
    client = Client()
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory()
    client.force_login(ops_user)

    def fake_update_return_case_status(*, actor, case, input_data):
        raise ReturnCaseWorkflowError("Invalid status transition.")

    monkeypatch.setattr(
        "returns.api.views.update_return_case_status",
        fake_update_return_case_status,
    )

    response = client.patch(
        f"/api/returns/{case.pk}/status/",
        data=json.dumps({"status": "approved"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid status transition."}


@pytest.mark.django_db
def test_return_case_note_api_creates_internal_note() -> None:
    """Ops users should be able to create internal case notes."""
    client = Client()
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory()
    client.force_login(ops_user)

    response = client.post(
        f"/api/returns/{case.pk}/notes/",
        data={"body": "Customer evidence matches the reported issue."},
    )

    assert response.status_code == 201
    assert response.json()["body"] == "Customer evidence matches the reported issue."
