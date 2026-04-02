# path: ml/feature_extraction.py
"""
Feature extraction for evidence-aware escalation scoring.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

from django.utils import timezone

from apps.returns.models import EvidenceDocumentKind

CONTRACT_PATH = Path(__file__).resolve().parent / "feature_contract.json"


def load_feature_names() -> list[str]:
    """
    Load the ordered feature names from the JSON contract.
    """

    contract = json.loads(CONTRACT_PATH.read_text())
    return contract["feature_names"]


def _order_value_band_flags(order_value: Decimal) -> dict[str, float]:
    """
    Bucket order value into three stable one-hot features.
    """

    value = float(order_value)
    return {
        "order_value_band_low": 1.0 if value < 50 else 0.0,
        "order_value_band_mid": 1.0 if 50 <= value < 150 else 0.0,
        "order_value_band_high": 1.0 if value >= 150 else 0.0,
    }


def extract_case_feature_vector(return_case) -> "OrderedDict[str, float]":
    """
    Extract an evidence-aware feature vector for a real return case.
    """

    documents = list(return_case.documents.all().order_by("created_at", "id"))
    now = timezone.now()

    image_count = sum(1 for doc in documents if doc.content_type in {"image/jpeg", "image/png"})
    pdf_count = sum(1 for doc in documents if doc.content_type == "application/pdf")
    customer_evidence = [
        doc for doc in documents if doc.document_kind == EvidenceDocumentKind.CUSTOMER_EVIDENCE
    ]
    merchant_documents = [
        doc for doc in documents if doc.document_kind == EvidenceDocumentKind.MERCHANT_RESPONSE
    ]

    first_customer_evidence_at = customer_evidence[0].created_at if customer_evidence else None
    hours_to_first_customer_evidence = (
        max((first_customer_evidence_at - return_case.opened_at).total_seconds() / 3600, 0.0)
        if first_customer_evidence_at
        else 0.0
    )

    feature_values: dict[str, float] = {
        "item_category_is_electronics": 1.0 if return_case.item_category == "electronics" else 0.0,
        "item_category_is_apparel": 1.0 if return_case.item_category == "apparel" else 0.0,
        "item_category_is_home": 1.0 if return_case.item_category == "home" else 0.0,
        "return_reason_is_damaged": 1.0 if return_case.return_reason == "damaged" else 0.0,
        "return_reason_is_not_as_described": (
            1.0 if return_case.return_reason == "not_as_described" else 0.0
        ),
        "return_reason_is_missing_parts": (
            1.0 if return_case.return_reason == "missing_parts" else 0.0
        ),
        "delivery_to_return_days": max(
            (return_case.opened_at - return_case.delivered_at).days,
            0,
        ),
        "customer_message_length": float(len(return_case.customer_message or "")),
        "prior_returns_count": float(return_case.prior_returns_count),
        "evidence_count": float(len(documents)),
        "customer_evidence_count": float(len(customer_evidence)),
        "merchant_document_count": float(len(merchant_documents)),
        "evidence_total_size_kb": float(sum(doc.size_bytes for doc in documents) / 1024),
        "has_image_evidence": 1.0 if image_count > 0 else 0.0,
        "has_pdf_evidence": 1.0 if pdf_count > 0 else 0.0,
        "hours_to_first_customer_evidence": float(hours_to_first_customer_evidence),
    }
    feature_values.update(_order_value_band_flags(return_case.order_value_gbp))

    ordered = OrderedDict()
    for feature_name in load_feature_names():
        ordered[feature_name] = float(feature_values.get(feature_name, 0.0))
    return ordered
