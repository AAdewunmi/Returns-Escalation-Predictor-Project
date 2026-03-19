# path: apps/ml/features.py
"""Deterministic feature extraction for ReturnHub escalation scoring."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

FEATURE_CONTRACT_VERSION = "return-risk-sprint2-v1"
FEATURE_CONTRACT_PATH = Path(__file__).resolve().parent / "contracts" / "return_case_features.json"

ITEM_CATEGORY_MAP = {
    "apparel": 1,
    "electronics": 2,
    "homeware": 3,
    "beauty": 4,
    "other": 99,
}

RETURN_REASON_MAP = {
    "damaged": 1,
    "wrong_item": 2,
    "wrong_size": 3,
    "not_as_described": 4,
    "changed_mind": 5,
    "other": 99,
}


def load_feature_contract() -> dict:
    """Load the committed feature contract file from disk."""
    return json.loads(FEATURE_CONTRACT_PATH.read_text(encoding="utf-8"))


def _encode_item_category(raw_value: str) -> int:
    """Encode item category into a stable integer bucket."""
    return ITEM_CATEGORY_MAP.get((raw_value or "").strip().lower(), ITEM_CATEGORY_MAP["other"])


def _encode_return_reason(raw_value: str) -> int:
    """Encode return reason into a stable integer bucket."""
    return RETURN_REASON_MAP.get((raw_value or "").strip().lower(), RETURN_REASON_MAP["other"])


def _delivery_to_return_days(case) -> int:
    """Compute elapsed whole days between delivery and case creation."""
    return max((case.created_at.date() - case.delivery_date).days, 0)


def _message_length_bucket(raw_value: str) -> int:
    """Bucket customer message length into coarse deterministic bands."""
    length = len((raw_value or "").strip())
    if length < 40:
        return 1
    if length < 120:
        return 2
    if length < 240:
        return 3
    return 4


def _order_value_band(value) -> int:
    """Map order value into a stable ordinal band."""
    numeric = float(value or 0)
    if numeric < 50:
        return 1
    if numeric < 150:
        return 2
    if numeric < 400:
        return 3
    return 4


def _prior_returns_count(case) -> int:
    """Count prior returns for the same customer, excluding the current case."""
    return case.customer.return_cases.exclude(pk=case.pk).count()


def extract_case_features(case) -> OrderedDict[str, int]:
    """Extract deterministic features in the exact order defined by the contract."""
    contract = load_feature_contract()
    features = OrderedDict(
        [
            ("item_category_code", _encode_item_category(case.item_category)),
            ("delivery_to_return_days", _delivery_to_return_days(case)),
            ("return_reason_code", _encode_return_reason(case.return_reason)),
            ("customer_message_length_bucket", _message_length_bucket(case.customer_message)),
            ("prior_returns_count", _prior_returns_count(case)),
            ("order_value_band", _order_value_band(case.order_value)),
        ]
    )

    expected_names = contract["feature_names"]
    if list(features.keys()) != expected_names:
        raise ValueError("Extracted feature names do not match the committed feature contract.")

    return features
