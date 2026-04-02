# path: apps/returns/tests/test_risk_scoring_service.py
"""
Tests for persisted evidence-aware scoring.
"""

from __future__ import annotations

import pytest

from apps.returns.ml.train import train_and_persist
from apps.returns.models import EvidenceDocumentKind
from apps.returns.services.risk import score_case_for_escalation
from apps.returns.tests.factories import EvidenceDocumentFactory, ReturnCaseFactory


@pytest.mark.django_db
def test_scoring_service_persists_risk_score_with_reason_codes(tmp_path, monkeypatch):
    """
    Scoring should persist a RiskScore row and stable reason codes.
    """

    monkeypatch.setattr("apps.returns.ml.train.ARTEFACTS_DIR", tmp_path / "artefacts")
    monkeypatch.setattr("apps.returns.ml.train.REGISTRY_PATH", tmp_path / "model_registry.json")
    registry = train_and_persist(seed=17)

    monkeypatch.setattr("apps.returns.services.risk.REGISTRY_PATH", tmp_path / "model_registry.json")

    return_case = ReturnCaseFactory()
    EvidenceDocumentFactory(
        return_case=return_case,
        document_kind=EvidenceDocumentKind.CUSTOMER_EVIDENCE,
        content_type="image/jpeg",
        size_bytes=4096,
    )

    risk_score = score_case_for_escalation(return_case=return_case, trigger_source="test_case")

    assert risk_score.model_version == registry["active_model_version"]
    assert isinstance(risk_score.reason_codes, list)
    assert risk_score.feature_snapshot["evidence_count"] == 1.0
