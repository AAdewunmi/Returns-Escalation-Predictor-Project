# path: ml/features.py
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


def _return_reason_is_damaged(raw_value: str) -> int:
    """Return a binary feature for damaged-item reasons."""
    return 1 if _encode_return_reason(raw_value) == 1 else 0


def _order_value_band_high(value) -> int:
    """Return a binary feature for the highest order-value band."""
    return 1 if _order_value_band(value) >= 4 else 0


def _hours_to_first_customer_evidence(case) -> float:
    """Measure the elapsed hours until the first customer evidence upload."""
    first_document = (
        case.documents.filter(actor_role="customer").order_by("created_at", "id").first()
    )
    if first_document is None:
        return 0.0

    elapsed_seconds = max(
        (first_document.created_at - case.created_at).total_seconds(),
        0.0,
    )
    return round(elapsed_seconds / 3600, 2)


def _evidence_count(case) -> int:
    """Count customer-provided evidence documents for the case."""
    return case.documents.filter(actor_role="customer").count()


def _merchant_document_count(case) -> int:
    """Count merchant-provided documents for the case."""
    return case.documents.filter(actor_role="merchant").count()


def _validate_feature_names(features: OrderedDict[str, int]) -> OrderedDict[str, int]:
    """Ensure a computed feature vector matches the committed contract order."""

    contract = load_feature_contract()
    expected_names = contract["feature_names"]
    if list(features.keys()) != expected_names:
        raise ValueError("Extracted feature names do not match the committed feature contract.")
    return features


def build_feature_vector(
    *,
    item_category: str,
    delivery_to_return_days: int,
    return_reason: str,
    customer_message: str,
    prior_returns_count: int,
    order_value,
    evidence_count: int = 0,
    hours_to_first_customer_evidence: float = 0.0,
    merchant_document_count: int = 0,
) -> OrderedDict[str, int]:
    """Build a contract-checked feature vector from primitive input values."""

    features = OrderedDict(
        [
            ("item_category_code", _encode_item_category(item_category)),
            ("delivery_to_return_days", max(int(delivery_to_return_days), 0)),
            ("return_reason_code", _encode_return_reason(return_reason)),
            ("return_reason_is_damaged", _return_reason_is_damaged(return_reason)),
            ("customer_message_length_bucket", _message_length_bucket(customer_message)),
            ("prior_returns_count", int(prior_returns_count)),
            ("order_value_band", _order_value_band(order_value)),
            ("order_value_band_high", _order_value_band_high(order_value)),
            ("evidence_count", int(evidence_count)),
            ("hours_to_first_customer_evidence", float(hours_to_first_customer_evidence)),
            ("merchant_document_count", int(merchant_document_count)),
        ]
    )

    return _validate_feature_names(features)


def extract_case_features(case) -> OrderedDict[str, int]:
    """Extract deterministic features in the exact order defined by the contract."""

    return build_feature_vector(
        item_category=case.item_category,
        delivery_to_return_days=_delivery_to_return_days(case),
        return_reason=case.return_reason,
        customer_message=case.customer_message,
        prior_returns_count=_prior_returns_count(case),
        order_value=case.order_value,
        evidence_count=_evidence_count(case),
        hours_to_first_customer_evidence=_hours_to_first_customer_evidence(case),
        merchant_document_count=_merchant_document_count(case),
    )
