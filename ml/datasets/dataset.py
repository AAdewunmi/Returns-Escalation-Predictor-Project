# path: ml/datasets/dataset.py
"""Pandas-friendly wrappers around the committed synthetic ML dataset."""

from __future__ import annotations

from typing import Any

from ml.training.baseline import DEFAULT_TRAINING_SEED, generate_synthetic_training_rows


def generate_synthetic_training_dataset(
    *,
    seed: int = DEFAULT_TRAINING_SEED,
    rows: int = 300,
) -> Any:
    """Return the seeded synthetic training rows as a DataFrame."""

    import pandas as pd

    training_rows = generate_synthetic_training_rows(seed=seed, size=rows)
    return pd.DataFrame([{**row["features"], "target": row["escalated"]} for row in training_rows])
