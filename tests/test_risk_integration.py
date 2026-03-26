# path: tests/test_risk_integration.py
"""Integration tests for risk persistence inside return workflows."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from returns.models import RiskScore
from returns.services.cases import (
    ReturnCaseCreateInput,
    StatusUpdateInput,
    create_return_case,
    update_return_case_status,
)
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
def test_create_return_case_persists_risk_score(monkeypatch) -> None:
    """Creating a case should persist a RiskScore record."""

    def fake_score_return_case(case):
        return RiskScore.objects.create(
            case=case,
            model_version="baseline-v1",
            score=Decimal("0.81"),
            label="high",
            reason_codes=["PRIOR_RETURNS_HIGH"],
            scored_at=case.created_at,
        )

    monkeypatch.setattr("returns.services.cases.score_return_case", fake_score_return_case)

    customer_user = UserFactory(email="risk-integration-create@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    merchant = MerchantProfileFactory()

    return_case = create_return_case(
        actor=customer_user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant,
            external_order_ref="ORD-3001",
            item_category="electronics",
            return_reason="damaged",
            customer_message="Screen cracked and box dented on arrival.",
            order_value=Decimal("299.99"),
            delivery_date=customer_profile.created_at.date(),
        ),
    )

    risk_score = RiskScore.objects.get(case=return_case)

    assert risk_score.label == "high"
    assert risk_score.reason_codes == ["PRIOR_RETURNS_HIGH"]


@pytest.mark.django_db
def test_update_return_case_status_keeps_one_risk_score_record(monkeypatch) -> None:
    """Status updates should not create a second RiskScore record."""

    ops_user = UserFactory(email="risk-integration-ops@example.com")
    add_group(ops_user, "ops")
    return_case = ReturnCaseFactory()
    RiskScore.objects.create(
        case=return_case,
        model_version="baseline-v1",
        score=Decimal("0.33"),
        label="low",
        reason_codes=["BASELINE_PATTERN_LOW_SIGNAL"],
        scored_at=return_case.created_at,
    )

    update_return_case_status(
        actor=ops_user,
        case=return_case,
        input_data=StatusUpdateInput(status="in_review", priority="high"),
    )

    assert RiskScore.objects.filter(case=return_case).count() == 1
    assert RiskScore.objects.get(case=return_case).label == "low"
