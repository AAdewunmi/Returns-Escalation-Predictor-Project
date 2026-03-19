# path: apps/ml/reason_codes.py
"""Reason-code generation for ReturnHub escalation scoring."""

from __future__ import annotations

REASON_CODE_SCHEMA_VERSION = "return-risk-reasons-sprint2-v1"


def build_reason_codes(features: dict[str, int]) -> list[dict[str, str]]:
    """Build stable reason-code objects from deterministic feature values."""
    codes: list[dict[str, str]] = []

    if features["delivery_to_return_days"] > 14:
        codes.append(
            {
                "code": "delayed_return_window",
                "direction": "up",
                "detail": "Delivery-to-return delay is relatively long.",
            }
        )

    if features["customer_message_length_bucket"] >= 3:
        codes.append(
            {
                "code": "detailed_customer_message",
                "direction": "up",
                "detail": "Customer message is long and detailed.",
            }
        )

    if features["prior_returns_count"] >= 2:
        codes.append(
            {
                "code": "repeat_return_history",
                "direction": "up",
                "detail": "Customer has multiple prior returns.",
            }
        )

    if features["order_value_band"] >= 4:
        codes.append(
            {
                "code": "high_order_value",
                "direction": "up",
                "detail": "Order value falls in the highest configured band.",
            }
        )

    if not codes:
        codes.append(
            {
                "code": "baseline_low_signal",
                "direction": "neutral",
                "detail": "Current case has limited escalation indicators.",
            }
        )

    return codes
