# path: tests/test_risk_score_persistence.py
"""DB-hitting integration tests for risk score persistence."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.apps import apps
from django.contrib.auth.models import Group

from returns.models import CaseEvent
from returns.services.cases import ReturnCaseCreateInput, create_return_case
from tests.factories import CustomerProfileFactory, MerchantProfileFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_case_creation_persists_risk_score_and_event() -> None:
    """Creating a case should persist placeholder risk output and an audit event."""
    try:
        risk_score_model = apps.get_model("returns", "RiskScore")
    except LookupError:
        pytest.skip("RiskScore model is not available in the current returns app.")

    customer_user = UserFactory(email="risk-create@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    merchant_profile = MerchantProfileFactory()

    case = create_return_case(
        actor=customer_user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant_profile,
            external_order_ref="ORDER-RISK-001",
            item_category="electronics",
            return_reason="damaged",
            customer_message="The parcel corner was crushed and the screen is black after power on.",
            order_value=Decimal("950.00"),
            delivery_date=customer_profile.created_at.date(),
        ),
    )

    risk_score = risk_score_model.objects.get(case=case)

    assert risk_score.model_version == "return-risk-placeholder-v1"
    assert risk_score.label in {"low", "medium", "high"}
    assert isinstance(risk_score.reason_codes, list)
    assert CaseEvent.objects.filter(case=case, event_type="risk_scored").exists()
