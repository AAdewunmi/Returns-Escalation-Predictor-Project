# path: tests/test_risk_score_persistence.py
"""DB-hitting integration tests for risk score persistence."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from returns.models import CaseEvent, RiskScore
from returns.services.cases import ReturnCaseCreateInput, create_return_case
from returns.services.risk_scoring import score_return_case
from tests.factories import CustomerProfileFactory, MerchantProfileFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_case_creation_persists_risk_score_and_event() -> None:
    """Creating a case should persist placeholder risk output and an audit event."""
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
            customer_message=(
                "The parcel corner was crushed and the screen is black after power on."
            ),
            order_value=Decimal("950.00"),
            delivery_date=customer_profile.created_at.date(),
        ),
    )

    risk_score = RiskScore.objects.get(case=case)

    assert risk_score.model_version == "return-risk-placeholder-v1"
    assert risk_score.label in {"low", "medium", "high"}
    assert isinstance(risk_score.reason_codes, list)
    assert CaseEvent.objects.filter(return_case=case, event_type="risk_scored").exists()


@pytest.mark.django_db
def test_score_return_case_updates_existing_risk_score_and_emits_event() -> None:
    """Re-scoring should update the one-to-one risk record and append an event."""
    customer_user = UserFactory(email="risk-update@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    merchant_profile = MerchantProfileFactory()

    case = create_return_case(
        actor=customer_user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant_profile,
            external_order_ref="ORDER-RISK-002",
            item_category="apparel",
            return_reason="damaged",
            customer_message="Initial damage report.",
            order_value=Decimal("100.00"),
            delivery_date=customer_profile.created_at.date(),
        ),
    )

    original_risk_score = RiskScore.objects.get(case=case)
    original_event_count = CaseEvent.objects.filter(
        return_case=case, event_type="risk_scored"
    ).count()

    case.customer_message = "A much longer message with additional return detail for rescoring."
    case.order_value = Decimal("450.00")
    case.save(update_fields=["customer_message", "order_value", "updated_at"])

    updated_risk_score = score_return_case(case)

    assert RiskScore.objects.filter(case=case).count() == 1
    assert updated_risk_score.pk == original_risk_score.pk
    assert updated_risk_score.scored_at >= original_risk_score.scored_at
    assert CaseEvent.objects.filter(return_case=case, event_type="risk_scored").count() == (
        original_event_count + 1
    )
    latest_event = CaseEvent.objects.filter(return_case=case, event_type="risk_scored").latest("id")
    assert latest_event.payload["model_version"] == updated_risk_score.model_version
    assert latest_event.payload["label"] == updated_risk_score.label
    assert latest_event.payload["score"] == str(updated_risk_score.score)
