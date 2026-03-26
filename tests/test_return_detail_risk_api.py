# path: tests/test_return_detail_risk_api.py
"""API tests for embedded risk data in return detail responses."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.ml.models import RiskScore
from apps.returns.tests.factories import ReturnCaseFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
def test_return_detail_api_embeds_latest_risk() -> None:
    """Return detail responses should include the latest persisted risk payload."""

    user = UserFactory()
    ops_group, _ = Group.objects.get_or_create(name="ops")
    user.groups.add(ops_group)

    return_case = ReturnCaseFactory()
    RiskScore.objects.create(
        return_case=return_case,
        model_version="baseline-v1",
        feature_contract_hash="hash-v1",
        reason_code_schema_version="v1",
        score="0.7400",
        label="medium",
        reason_codes=["ORDER_VALUE_BAND_HIGH", "CUSTOMER_MESSAGE_LONG"],
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(
        reverse("return-case-detail-api", kwargs={"case_id": return_case.id})
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["risk"]["label"] == "medium"
    assert payload["risk"]["score"] == "0.7400"
    assert payload["risk"]["reason_codes"] == [
        "ORDER_VALUE_BAND_HIGH",
        "CUSTOMER_MESSAGE_LONG",
    ]
