# path: tests/test_scoring.py
"""Unit tests for deterministic placeholder risk scoring."""

from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal

import pytest

from ml.reason_codes import build_reason_codes
from ml.scoring import _quantise_score, score_case_features


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.444, Decimal("0.44")),
        (0.445, Decimal("0.45")),
    ],
)
def test_quantise_score_uses_half_up_rounding(value: float, expected: Decimal) -> None:
    """Quantisation should be stable and use Decimal half-up rounding."""
    assert _quantise_score(value) == expected


@pytest.mark.parametrize(
    ("features", "expected_label", "expected_score"),
    [
        (
            OrderedDict(
                [
                    ("item_category_code", 1),
                    ("delivery_to_return_days", 0),
                    ("return_reason_code", 2),
                    ("customer_message_length_bucket", 1),
                    ("prior_returns_count", 0),
                    ("order_value_band", 1),
                ]
            ),
            "low",
            Decimal("0.22"),
        ),
        (
            OrderedDict(
                [
                    ("item_category_code", 1),
                    ("delivery_to_return_days", 5),
                    ("return_reason_code", 2),
                    ("customer_message_length_bucket", 1),
                    ("prior_returns_count", 0),
                    ("order_value_band", 2),
                ]
            ),
            "medium",
            Decimal("0.42"),
        ),
        (
            OrderedDict(
                [
                    ("item_category_code", 1),
                    ("delivery_to_return_days", 30),
                    ("return_reason_code", 1),
                    ("customer_message_length_bucket", 4),
                    ("prior_returns_count", 5),
                    ("order_value_band", 4),
                ]
            ),
            "high",
            Decimal("0.95"),
        ),
    ],
)
def test_score_case_features_assigns_expected_labels_and_bounds(
    features, expected_label, expected_score
) -> None:
    """Scoring should produce stable labels across low, medium, and high thresholds."""
    prediction = score_case_features(features)

    assert prediction.label == expected_label
    assert prediction.score == expected_score


def test_build_reason_codes_returns_baseline_when_no_signals_present() -> None:
    """Reason codes should fall back to a neutral baseline when no thresholds are met."""
    features = {
        "delivery_to_return_days": 3,
        "customer_message_length_bucket": 1,
        "prior_returns_count": 0,
        "order_value_band": 1,
    }

    assert build_reason_codes(features) == [
        {
            "code": "baseline_low_signal",
            "direction": "neutral",
            "detail": "Current case has limited escalation indicators.",
        }
    ]


def test_build_reason_codes_includes_all_triggered_signals() -> None:
    """Reason-code generation should append every triggered escalation indicator."""
    features = {
        "delivery_to_return_days": 18,
        "customer_message_length_bucket": 3,
        "prior_returns_count": 2,
        "order_value_band": 4,
    }

    assert [item["code"] for item in build_reason_codes(features)] == [
        "delayed_return_window",
        "detailed_customer_message",
        "repeat_return_history",
        "high_order_value",
    ]
