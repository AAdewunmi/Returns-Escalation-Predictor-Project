# path: tests/test_risk_scoring_service.py
"""Tests for the current risk scoring persistence service."""

from __future__ import annotations

from decimal import Decimal

import pytest

from returns.models import RiskScore
from returns.services.risk import score_case_and_persist
from tests.factories import ReturnCaseFactory


@pytest.mark.django_db
def test_risk_service_persists_explainable_output_and_trigger_source(monkeypatch) -> None:
    """Risk persistence should keep reason codes and audit the trigger source."""

    case = ReturnCaseFactory()

    class FakePrediction:
        model_version = "evidence-aware-v1"
        score = Decimal("0.81")
        label = "high"
        reason_codes = [
            {
                "code": "missing_customer_evidence",
                "direction": "up",
                "detail": "Customer has not submitted supporting evidence yet.",
            }
        ]

    monkeypatch.setattr(
        "returns.services.risk._get_scoring_result",
        lambda return_case: FakePrediction,
    )

    risk_score = score_case_and_persist(case, triggered_by="test_case")

    assert isinstance(risk_score, RiskScore)
    assert risk_score.model_version == "evidence-aware-v1"
    assert risk_score.reason_codes == FakePrediction.reason_codes
    latest_event = case.events.latest("id")
    assert latest_event.payload["triggered_by"] == "test_case"
    assert latest_event.payload["reason_codes"] == FakePrediction.reason_codes


@pytest.mark.django_db
def test_risk_service_updates_existing_score_instead_of_creating_duplicate(monkeypatch) -> None:
    """Re-scoring should update the one-to-one risk record for the case."""

    case = ReturnCaseFactory()

    class FirstPrediction:
        model_version = "model-v1"
        score = Decimal("0.44")
        label = "low"
        reason_codes = []

    class SecondPrediction:
        model_version = "model-v2"
        score = Decimal("0.79")
        label = "high"
        reason_codes = [
            {
                "code": "high_order_value",
                "direction": "up",
                "detail": "Order value falls in the highest configured band.",
            }
        ]

    monkeypatch.setattr(
        "returns.services.risk._get_scoring_result",
        lambda return_case: FirstPrediction,
    )
    original = score_case_and_persist(case, triggered_by="initial_score")

    monkeypatch.setattr(
        "returns.services.risk._get_scoring_result",
        lambda return_case: SecondPrediction,
    )
    updated = score_case_and_persist(case, triggered_by="rescored")

    assert RiskScore.objects.filter(case=case).count() == 1
    assert updated.pk == original.pk
    assert updated.model_version == "model-v2"
    assert updated.reason_codes == SecondPrediction.reason_codes
