# path: tests/test_scoring.py
"""Unit tests for deterministic placeholder risk scoring."""

from __future__ import annotations

from collections import OrderedDict

from ml.scoring import score_case_features


def test_placeholder_scoring_is_deterministic() -> None:
    """The same feature dictionary should always produce the same prediction."""
    features = OrderedDict(
        [
            ("item_category_code", 2),
            ("delivery_to_return_days", 18),
            ("return_reason_code", 1),
            ("customer_message_length_bucket", 4),
            ("prior_returns_count", 3),
            ("order_value_band", 4),
        ]
    )

    first_prediction = score_case_features(features)
    second_prediction = score_case_features(features)

    assert first_prediction == second_prediction
    assert first_prediction.label == "high"
    assert isinstance(first_prediction.reason_codes, list)
    assert all("code" in item and "detail" in item for item in first_prediction.reason_codes)
