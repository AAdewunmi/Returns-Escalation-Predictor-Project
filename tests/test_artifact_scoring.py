# path: tests/test_artifact_scoring.py
"""Tests for artefact-backed ML scoring and workflow fallback."""

from __future__ import annotations

import json
import pickle
from decimal import Decimal
from pathlib import Path

import pytest

from ml.services.scoring import (
    ArtifactScoringUnavailableError,
    label_from_score,
    load_active_model,
)
from ml.services.scoring import score_return_case as score_artifact_return_case
from returns.models import RiskScore
from returns.services.risk_scoring import score_return_case as persist_risk_score
from tests.factories import ReturnCaseFactory


class FixedProbabilityModel:
    """Simple picklable model stub for artefact-backed scoring tests."""

    def __init__(self, probability: float) -> None:
        self.probability = probability

    def predict_proba(self, rows: list[dict[str, int]]) -> list[list[float]]:
        """Return a stable binary probability payload for each feature row."""

        return [[1.0 - self.probability, self.probability] for _ in rows]


def write_active_model_artifacts(
    *,
    base_dir: Path,
    version: str,
    probability: float,
    feature_contract_hash: str = "contract-hash-123",
) -> None:
    """Write a registry entry plus matching model and metadata artefacts."""

    registry_dir = base_dir / "ml" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "model_registry.json").write_text(
        json.dumps(
            {
                "active_model": {
                    "version": version,
                    "model_type": "logistic_regression",
                    "contract_version": "return-risk-sprint2-v1",
                    "reason_code_schema_version": "return-risk-reasons-sprint2-v1",
                    "status": "active",
                }
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    artifact_dir = base_dir / "ml_artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with (artifact_dir / f"{version}.pkl").open("wb") as artifact_file:
        pickle.dump(FixedProbabilityModel(probability), artifact_file)

    (artifact_dir / f"{version}.json").write_text(
        json.dumps(
            {
                "model_version": version,
                "feature_contract_hash": feature_contract_hash,
                "reason_code_schema_version": "return-risk-reasons-sprint2-v1",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


@pytest.mark.django_db
def test_artifact_backed_scoring_loads_active_model_and_scores_return_case(
    settings, tmp_path
) -> None:
    """The artefact-backed scorer should load the active model and return a payload."""

    settings.BASE_DIR = tmp_path
    version = "baseline-logreg-v1-seed-7-rows-500"
    write_active_model_artifacts(base_dir=tmp_path, version=version, probability=0.82)
    case = ReturnCaseFactory(
        item_category="electronics",
        return_reason="damaged",
        customer_message=(
            "Customer provided a long, detailed message about repeated faults, repeated resets, "
            "serial numbers, packaging damage, and multiple troubleshooting attempts before "
            "requesting escalation."
        ),
        order_value=Decimal("499.99"),
    )

    result = score_artifact_return_case(case)

    assert result.model_version == version
    assert result.score == Decimal("0.82")
    assert result.label == "high"
    assert result.feature_contract_hash == "contract-hash-123"
    assert result.reason_code_schema_version == "return-risk-reasons-sprint2-v1"
    reason_codes = [item["code"] for item in result.reason_codes]
    assert "delayed_return_window" in reason_codes
    assert "detailed_customer_message" in reason_codes
    assert "high_order_value" in reason_codes


def test_load_active_model_raises_clean_error_when_artifact_is_missing(settings, tmp_path) -> None:
    """Missing artefacts should raise a domain-specific error."""

    settings.BASE_DIR = tmp_path
    registry_dir = tmp_path / "ml" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "model_registry.json").write_text(
        json.dumps(
            {
                "active_model": {
                    "version": "baseline-logreg-v1",
                    "model_type": "logistic_regression",
                    "contract_version": "return-risk-sprint2-v1",
                    "reason_code_schema_version": "return-risk-reasons-sprint2-v1",
                    "status": "active",
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ArtifactScoringUnavailableError,
        match="Active ML model artefact is unavailable or invalid.",
    ):
        load_active_model()


def test_load_active_model_raises_when_metadata_lacks_feature_contract_hash(
    settings, tmp_path
) -> None:
    """Metadata must include the feature contract hash used by the active model."""

    settings.BASE_DIR = tmp_path
    version = "baseline-logreg-v1-seed-7-rows-500"
    write_active_model_artifacts(base_dir=tmp_path, version=version, probability=0.61)
    metadata_path = tmp_path / "ml_artifacts" / f"{version}.json"
    metadata_path.write_text(
        json.dumps(
            {
                "model_version": version,
                "reason_code_schema_version": "return-risk-reasons-sprint2-v1",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ArtifactScoringUnavailableError,
        match="Active ML model metadata is missing feature_contract_hash.",
    ):
        load_active_model()


@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (0.80, "high"),
        (0.45, "medium"),
        (0.44, "low"),
    ],
)
def test_label_from_score_uses_stable_thresholds(score: float, expected_label: str) -> None:
    """Label assignment should stay stable at the configured probability thresholds."""

    assert label_from_score(score) == expected_label


@pytest.mark.django_db
def test_workflow_scoring_uses_artifact_backed_model_when_available(settings, tmp_path) -> None:
    """The live workflow scorer should persist output from the active model artefact."""

    settings.BASE_DIR = tmp_path
    version = "baseline-logreg-v1-seed-7-rows-500"
    write_active_model_artifacts(base_dir=tmp_path, version=version, probability=0.61)
    case = ReturnCaseFactory(
        item_category="electronics",
        return_reason="damaged",
        customer_message=(
            "The casing is cracked, multiple images are attached for review, the hinge alignment "
            "is off, and the customer has described several failed attempts to use the item "
            "safely since delivery."
        ),
        order_value=Decimal("450.00"),
    )

    risk_score = persist_risk_score(case)

    assert risk_score.model_version == version
    assert risk_score.score == Decimal("0.61")
    assert risk_score.label == "medium"
    assert isinstance(risk_score.reason_codes, list)
    assert {item["code"] for item in risk_score.reason_codes} >= {
        "delayed_return_window",
        "detailed_customer_message",
        "high_order_value",
    }
    assert RiskScore.objects.get(case=case).pk == risk_score.pk


@pytest.mark.django_db
def test_workflow_scoring_falls_back_to_placeholder_when_artifact_scoring_fails(
    monkeypatch, caplog
) -> None:
    """The live workflow scorer should fall back without failing case scoring."""

    case = ReturnCaseFactory()

    def fake_score_active_model(case):
        raise ArtifactScoringUnavailableError("missing artefact")

    monkeypatch.setattr("returns.services.risk_scoring.score_active_model", fake_score_active_model)

    risk_score = persist_risk_score(case)

    assert risk_score.model_version
    assert risk_score.label in {"low", "medium", "high"}
    assert isinstance(risk_score.reason_codes, list)
    assert "Falling back to placeholder risk scoring" in caplog.text
