# path: tests/test_return_detail_risk_api.py
"""API tests for embedded risk data in return detail responses."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from returns.models import RiskScore
from tests.factories import ReturnCaseFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_return_detail_api_embeds_latest_risk_for_ops_users() -> None:
    """Return detail responses should include persisted risk payloads for ops users."""

    user = UserFactory(email="detail-risk-ops@example.com")
    add_group(user, "ops")
    return_case = ReturnCaseFactory()
    RiskScore.objects.create(
        case=return_case,
        model_version="baseline-v1",
        score=Decimal("0.74"),
        label="medium",
        reason_codes=[
            {"code": "high_order_value", "direction": "up", "detail": "High value order."},
            {
                "code": "detailed_customer_message",
                "direction": "up",
                "detail": "Customer message is long.",
            },
        ],
        scored_at=datetime.datetime(2026, 3, 1, 10, 0, 0, tzinfo=datetime.UTC),
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/returns/{return_case.pk}/")

    assert response.status_code == 200
    payload = response.json()

    assert payload["risk"]["label"] == "medium"
    assert payload["risk"]["score"] == "0.74"
    assert payload["risk"]["reason_codes"] == [
        {"code": "high_order_value", "direction": "up", "detail": "High value order."},
        {
            "code": "detailed_customer_message",
            "direction": "up",
            "detail": "Customer message is long.",
        },
    ]
