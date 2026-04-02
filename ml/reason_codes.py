# path: apps/ml/reason_codes.py
"""Stable reason-code generation for escalation-risk scoring."""

from __future__ import annotations

from typing import Callable

REASON_CODE_SCHEMA_VERSION = "return-risk-reasons-sprint3-v1"

ReasonCodeRule = tuple[str, str, str, Callable[[dict[str, float | int]], bool]]

REASON_CODE_RULES: list[ReasonCodeRule] = [
    (
        "delayed_return_window",
        "up",
        "Delivery-to-return delay is relatively long.",
        lambda features: float(features.get("delivery_to_return_days", 0)) > 14.0,
    ),
    (
        "detailed_customer_message",
        "up",
        "Customer message is long and detailed.",
        lambda features: float(features.get("customer_message_length_bucket", 0)) >= 3.0,
    ),
    (
        "repeat_return_history",
        "up",
        "Customer has multiple prior returns.",
        lambda features: float(features.get("prior_returns_count", 0)) >= 2.0,
    ),
    (
        "high_order_value",
        "up",
        "Order value falls in the highest configured band.",
        lambda features: (
            float(features.get("order_value_band_high", 0)) == 1.0
            or float(features.get("order_value_band", 0)) >= 4.0
        ),
    ),
    (
        "missing_customer_evidence",
        "up",
        "Customer has not submitted supporting evidence yet.",
        lambda features: (
            "evidence_count" in features and float(features.get("evidence_count", 0)) == 0.0
        ),
    ),
    (
        "damaged_item_reason",
        "up",
        "Return reason indicates the item was reported as damaged.",
        lambda features: (
            float(features.get("return_reason_is_damaged", 0)) == 1.0
            or float(features.get("return_reason_code", 0)) == 1.0
        ),
    ),
    (
        "slow_evidence_follow_up",
        "up",
        "Initial customer evidence arrived after a relatively long delay.",
        lambda features: (
            "hours_to_first_customer_evidence" in features
            and float(features.get("hours_to_first_customer_evidence", 0)) >= 24.0
        ),
    ),
    (
        "repeat_return_customer",
        "up",
        "Customer has a substantial prior return history.",
        lambda features: float(features.get("prior_returns_count", 0)) >= 3.0,
    ),
    (
        "merchant_has_not_replied",
        "up",
        "Merchant has not added any supporting documents or responses.",
        lambda features: (
            "merchant_document_count" in features
            and float(features.get("merchant_document_count", 0)) == 0.0
        ),
    ),
]


def _build_reason_code(code: str, direction: str, detail: str) -> dict[str, str]:
    """Return the structured reason-code object used by the scoring payload."""

    return {
        "code": code,
        "direction": direction,
        "detail": detail,
    }


def build_reason_codes(features: dict[str, float | int]) -> list[dict[str, str]]:
    """Build stable ordered reason-code objects from the feature snapshot."""

    codes: list[dict[str, str]] = []
    seen_codes: set[str] = set()

    for code, direction, detail, predicate in REASON_CODE_RULES:
        if predicate(features) and code not in seen_codes:
            codes.append(_build_reason_code(code, direction, detail))
            seen_codes.add(code)

    if not codes:
        codes.append(
            _build_reason_code(
                "baseline_low_signal",
                "neutral",
                "Current case has limited escalation indicators.",
            )
        )

    return codes
