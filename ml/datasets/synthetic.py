# path: ml/datasets/synthetic.py
"""Synthetic dataset generation for ReturnHub risk model development."""

from __future__ import annotations

import csv
import random
from pathlib import Path


def generate_synthetic_rows(*, seed: int = 7, size: int = 250) -> list[dict]:
    """Generate deterministic operational-style synthetic training rows."""
    rng = random.Random(seed)
    categories = ["apparel", "electronics", "homeware", "beauty"]
    reasons = ["damaged", "wrong_item", "wrong_size", "not_as_described", "changed_mind"]

    rows: list[dict] = []
    for _ in range(size):
        delivery_to_return_days = rng.randint(0, 30)
        prior_returns_count = rng.randint(0, 5)
        order_value_band = rng.randint(1, 4)
        message_bucket = rng.randint(1, 4)
        return_reason = rng.choice(reasons)
        item_category = rng.choice(categories)

        label = (
            1
            if (
                delivery_to_return_days > 14
                or prior_returns_count >= 2
                or (return_reason == "damaged" and order_value_band >= 3)
            )
            else 0
        )

        rows.append(
            {
                "item_category": item_category,
                "return_reason": return_reason,
                "delivery_to_return_days": delivery_to_return_days,
                "customer_message_length_bucket": message_bucket,
                "prior_returns_count": prior_returns_count,
                "order_value_band": order_value_band,
                "label": label,
            }
        )
    return rows


def write_synthetic_rows_to_csv(*, output_path: Path, rows: list[dict]) -> None:
    """Write deterministic rows to CSV with a stable header order."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "item_category",
        "return_reason",
        "delivery_to_return_days",
        "customer_message_length_bucket",
        "prior_returns_count",
        "order_value_band",
        "label",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
