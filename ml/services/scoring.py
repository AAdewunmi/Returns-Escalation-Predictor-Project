# path: ml/services/scoring.py
"""Inference services for ReturnHub escalation-risk scoring."""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from django.conf import settings

from ml.features import extract_case_features
from ml.reason_codes import build_reason_codes
from ml.services.model_registry import get_active_model_entry
from returns.models import ReturnCase


@dataclass(frozen=True)
class ScoringResult:
    """The persisted scoring payload for a return case."""

    score: Decimal
    label: str
    reason_codes: list[str]
    model_version: str
    feature_contract_hash: str
    reason_code_schema_version: str


def get_registry_path() -> Path:
    """Return the default registry path for ML artefacts."""

    return Path(settings.BASE_DIR) / "ml" / "registry" / "model_registry.json"


def get_artifact_dir() -> Path:
    """Return the default output directory for trained model artefacts."""

    return Path(settings.BASE_DIR) / "ml_artifacts"


def get_model_path(model_version: str) -> Path:
    """Build the expected model artefact path for a registered model version."""

    return get_artifact_dir() / f"{model_version}.pkl"


def get_metadata_path(model_version: str) -> Path:
    """Build the expected metadata path for a registered model version."""

    return get_artifact_dir() / f"{model_version}.json"


def load_model_metadata(model_version: str) -> dict[str, object]:
    """Load metadata produced during training for the supplied model version."""

    metadata_path = get_metadata_path(model_version)
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def label_from_score(score: float) -> str:
    """Map a probability score to a stable operational label."""

    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def quantise_score(score: float) -> Decimal:
    """Normalise a score to the persisted decimal precision."""

    return Decimal(str(score)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def generate_reason_codes(feature_vector: dict[str, int]) -> list[str]:
    """Generate stable reason-code identifiers from extracted features."""

    return [item["code"] for item in build_reason_codes(feature_vector)]


def score_return_case(return_case: ReturnCase) -> ScoringResult:
    """Score a return case using the active registered model."""

    registry_entry = get_active_model_entry(get_registry_path())
    with get_model_path(registry_entry.version).open("rb") as artifact_file:
        model = pickle.load(artifact_file)
    metadata = load_model_metadata(registry_entry.version)

    feature_vector = extract_case_features(return_case)
    probability = float(model.predict_proba([feature_vector])[0][1])

    return ScoringResult(
        score=quantise_score(probability),
        label=label_from_score(probability),
        reason_codes=generate_reason_codes(feature_vector),
        model_version=registry_entry.version,
        feature_contract_hash=str(metadata["feature_contract_hash"]),
        reason_code_schema_version=registry_entry.reason_code_schema_version,
    )
