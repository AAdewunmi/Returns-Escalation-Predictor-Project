# path: apps/ml/scoring.py
"""Deterministic placeholder scoring for ReturnHub escalation risk."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from ml.reason_codes import build_reason_codes
from ml.registry import load_active_model


@dataclass(frozen=True)
class RiskPrediction:
    """Canonical risk prediction payload."""

    model_version: str
    score: Decimal
    label: str
    reason_codes: list[dict[str, str]]


def _quantise_score(value: float) -> Decimal:
    """Round a floating score into a stable two-decimal Decimal."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score_case_features(features: dict[str, int]) -> RiskPrediction:
    """Score a feature dictionary using a deterministic weighted placeholder."""
    registry_entry = load_active_model()

    raw_score = (
        (features["delivery_to_return_days"] * 0.02)
        + (features["customer_message_length_bucket"] * 0.12)
        + (features["prior_returns_count"] * 0.18)
        + (features["order_value_band"] * 0.10)
        + (0.20 if features["return_reason_code"] == 1 else 0.00)
    )
    bounded_score = max(0.05, min(raw_score, 0.95))
    score = _quantise_score(bounded_score)

    if score >= Decimal("0.70"):
        label = "high"
    elif score >= Decimal("0.40"):
        label = "medium"
    else:
        label = "low"

    return RiskPrediction(
        model_version=registry_entry.version,
        score=score,
        label=label,
        reason_codes=build_reason_codes(features),
    )
