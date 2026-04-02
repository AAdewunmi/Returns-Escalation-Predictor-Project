# path: apps/returns/ml/dataset.py
"""
Synthetic evidence-aware training dataset generation.
"""

from __future__ import annotations

import random

import pandas as pd


def generate_synthetic_training_dataset(seed: int = 17, rows: int = 300) -> pd.DataFrame:
    """
    Generate a deterministic training dataset for local and CI use.
    """

    rng = random.Random(seed)
    data: list[dict[str, float | int]] = []

    for _ in range(rows):
        item_category = rng.choice(["electronics", "apparel", "home"])
        return_reason = rng.choice(["damaged", "not_as_described", "missing_parts"])
        order_value = rng.choice([29, 79, 149, 249])
        prior_returns = rng.randint(0, 5)
        message_length = rng.randint(20, 420)
        evidence_count = rng.randint(0, 4)
        customer_evidence_count = rng.randint(0, evidence_count)
        merchant_document_count = rng.randint(0, 2)
        has_image = 1 if evidence_count > 0 and rng.random() > 0.35 else 0
        has_pdf = 1 if evidence_count > 0 and rng.random() > 0.45 else 0
        evidence_total_size_kb = rng.randint(0, 2048) if evidence_count else 0
        hours_to_first_customer_evidence = rng.choice([0, 2, 8, 24, 72]) if evidence_count else 0
        delivery_to_return_days = rng.randint(0, 14)

        target = 0
        if return_reason == "damaged":
            target += 1
        if item_category == "electronics":
            target += 1
        if prior_returns >= 3:
            target += 1
        if evidence_count == 0:
            target += 1
        if hours_to_first_customer_evidence >= 24:
            target += 1
        if order_value >= 150:
            target += 1

        data.append(
            {
                "item_category_is_electronics": 1 if item_category == "electronics" else 0,
                "item_category_is_apparel": 1 if item_category == "apparel" else 0,
                "item_category_is_home": 1 if item_category == "home" else 0,
                "return_reason_is_damaged": 1 if return_reason == "damaged" else 0,
                "return_reason_is_not_as_described": 1 if return_reason == "not_as_described" else 0,
                "return_reason_is_missing_parts": 1 if return_reason == "missing_parts" else 0,
                "delivery_to_return_days": delivery_to_return_days,
                "customer_message_length": message_length,
                "prior_returns_count": prior_returns,
                "order_value_band_low": 1 if order_value < 50 else 0,
                "order_value_band_mid": 1 if 50 <= order_value < 150 else 0,
                "order_value_band_high": 1 if order_value >= 150 else 0,
                "evidence_count": evidence_count,
                "customer_evidence_count": customer_evidence_count,
                "merchant_document_count": merchant_document_count,
                "evidence_total_size_kb": evidence_total_size_kb,
                "has_image_evidence": has_image,
                "has_pdf_evidence": has_pdf,
                "hours_to_first_customer_evidence": hours_to_first_customer_evidence,
                "target": 1 if target >= 3 else 0,
            }
        )

    return pd.DataFrame(data)
