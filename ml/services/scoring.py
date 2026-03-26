# path: apps/ml/services/scoring.py
"""Inference services for ReturnHub escalation-risk scoring."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Mapping

import joblib
from django.conf import settings

from apps.ml.contracts import REASON_CODE_SCHEMA_VERSION
from apps.ml.features.extraction import extract_features_from_return_case
from apps.ml.services.model_registry import get_active_model_entry
from apps.returns.models import ReturnCase


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

    return Path(settings.BASE_DIR) / "ml_artifacts" / "registry.json"


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


def generate_reason_codes(
    feature_vector: Mapping[str, Any],
    *,
    score: float,
) -> list[str]:
    """
    Generate stable reason codes in a deterministic order.

    Ordering is explicit. The service does not sort codes by any dynamic score,
    which avoids unstable output across repeated runs.
    """

    reason_codes: list[str] = []

    if int(feature_vector.get("prior_returns_count", 0)) >= 3:
        reason_codes.append("PRIOR_RETURNS_HIGH")
    if int(feature_vector.get("delivery_to_return_days", 99)) <= 2:
        reason_codes.append("RETURN_AFTER_DELIVERY_SHORT")
    if str(feature_vector.get("order_value_band", "")) in {"high", "premium"}:
        reason_codes.append("ORDER_VALUE_BAND_HIGH")
    if int(feature_vector.get("customer_message_length", 0)) >= 600:
        reason_codes.append("CUSTOMER_MESSAGE_LONG")
    if int(feature_vector.get("evidence_count", 0)) == 0 and score >= 0.45:
        reason_codes.append("EVIDENCE_MISSING_EARLY")

    if not reason_codes:
        reason_codes.append("BASELINE_PATTERN_LOW_SIGNAL")

    return reason_codes[:3]


def score_return_case(return_case: ReturnCase) -> ScoringResult:
    """Score a return case using the active registered model."""

    registry_entry = get_active_model_entry(get_registry_path())
    model = joblib.load(registry_entry.model_path)

    feature_vector = extract_features_from_return_case(return_case)
    probability = float(model.predict_proba([feature_vector])[0][1])

    return ScoringResult(
        score=quantise_score(probability),
        label=label_from_score(probability),
        reason_codes=generate_reason_codes(feature_vector, score=probability),
        model_version=registry_entry.model_version,
        feature_contract_hash=registry_entry.feature_contract_hash,
        reason_code_schema_version=REASON_CODE_SCHEMA_VERSION,
    )
