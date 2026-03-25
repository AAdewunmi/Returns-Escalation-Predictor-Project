# path: ml/training/baseline.py
"""Baseline escalation-risk model training for ReturnHub."""

from __future__ import annotations

import hashlib
import json
import pickle
import random
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from typing import Any

from ml.features import (
    FEATURE_CONTRACT_PATH,
    FEATURE_CONTRACT_VERSION,
    _encode_item_category,
    _encode_return_reason,
    _message_length_bucket,
    _order_value_band,
)
from ml.reason_codes import REASON_CODE_SCHEMA_VERSION

DEFAULT_TRAINING_SEED = 7
DEFAULT_TRAINING_SIZE = 500


def _get_feature_contract_hash() -> str:
    """Return a stable hash of the committed feature contract file."""

    return hashlib.sha256(FEATURE_CONTRACT_PATH.read_bytes()).hexdigest()


def _extract_features_from_payload(payload: dict[str, Any]) -> dict[str, int]:
    """Map a synthetic payload into the committed feature contract shape."""

    return {
        "item_category_code": _encode_item_category(payload["item_category"]),
        "delivery_to_return_days": int(payload["delivery_to_return_days"]),
        "return_reason_code": _encode_return_reason(payload["return_reason"]),
        "customer_message_length_bucket": _message_length_bucket(
            "x" * int(payload["customer_message_length"])
        ),
        "prior_returns_count": int(payload["prior_returns_count"]),
        "order_value_band": _order_value_band(payload["order_value_band_value"]),
    }


@dataclass(frozen=True)
class TrainingOutput:
    """Metadata returned after training and saving a model artefact."""

    model_version: str
    model_path: Path
    metadata_path: Path
    metrics: dict[str, float]
    feature_contract_hash: str
    training_rows: int


def generate_synthetic_training_rows(
    *,
    seed: int = DEFAULT_TRAINING_SEED,
    size: int = DEFAULT_TRAINING_SIZE,
) -> list[dict[str, Any]]:
    """
    Generate deterministic synthetic training rows.

    The generator is simple on purpose. The goal is reproducibility and
    operational realism rather than a sophisticated synthetic world model.
    """

    generator = random.Random(seed)
    rows: list[dict[str, Any]] = []

    for _ in range(size):
        prior_returns_count = generator.randint(0, 5)
        delivery_to_return_days = generator.randint(0, 30)
        customer_message_length = generator.randint(30, 1200)
        evidence_count = generator.randint(0, 3)

        item_category = generator.choice(
            ["electronics", "fashion", "home", "beauty", "sports"]
        )
        return_reason = generator.choice(
            ["damaged", "wrong_item", "not_as_described", "changed_mind", "missing_parts"]
        )
        order_value_band = generator.choice(["low", "mid", "high", "premium"])

        risk_points = 0
        if prior_returns_count >= 3:
            risk_points += 2
        if delivery_to_return_days <= 2:
            risk_points += 2
        if customer_message_length >= 600:
            risk_points += 1
        if evidence_count == 0 and return_reason in {"damaged", "missing_parts"}:
            risk_points += 1
        if order_value_band in {"high", "premium"}:
            risk_points += 1
        if item_category == "electronics":
            risk_points += 1

        escalated = 1 if risk_points >= 4 else 0

        payload = {
            "item_category": item_category,
            "delivery_to_return_days": delivery_to_return_days,
            "return_reason": return_reason,
            "customer_message_length": customer_message_length,
            "prior_returns_count": prior_returns_count,
            "order_value_band_value": {
                "low": 25,
                "mid": 100,
                "high": 250,
                "premium": 500,
            }[order_value_band],
            "evidence_count": evidence_count,
        }

        rows.append(
            {
                "features": _extract_features_from_payload(payload),
                "escalated": escalated,
            }
        )

    return rows


def train_and_save_baseline_model(
    output_dir: Path,
    *,
    seed: int = DEFAULT_TRAINING_SEED,
    size: int = DEFAULT_TRAINING_SIZE,
) -> TrainingOutput:
    """Train the baseline model and save its artefact plus metadata."""

    from sklearn.feature_extraction import DictVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, roc_auc_score
    from sklearn.pipeline import Pipeline

    training_rows = generate_synthetic_training_rows(seed=seed, size=size)
    feature_rows = [row["features"] for row in training_rows]
    labels = [row["escalated"] for row in training_rows]

    pipeline = Pipeline(
        steps=[
            ("vectorizer", DictVectorizer(sparse=False)),
            (
                "model",
                LogisticRegression(
                    max_iter=500,
                    random_state=seed,
                    solver="liblinear",
                ),
            ),
        ]
    )
    pipeline.fit(feature_rows, labels)

    probabilities = pipeline.predict_proba(feature_rows)[:, 1]
    predictions = pipeline.predict(feature_rows)

    metrics = {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "roc_auc": round(float(roc_auc_score(labels, probabilities)), 4),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    model_version = f"baseline-logreg-v1-seed-{seed}-rows-{size}"
    model_path = output_dir / f"{model_version}.pkl"
    metadata_path = output_dir / f"{model_version}.json"
    feature_contract_hash = _get_feature_contract_hash()

    with model_path.open("wb") as artifact_file:
        pickle.dump(pipeline, artifact_file)

    metadata = {
        "model_version": model_version,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "feature_contract_hash": feature_contract_hash,
        "reason_code_schema_version": REASON_CODE_SCHEMA_VERSION,
        "training_rows": size,
        "training_seed": seed,
        "metrics": metrics,
        "trained_at": datetime.now(tz=dt_timezone.utc).isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))

    return TrainingOutput(
        model_version=model_version,
        model_path=model_path,
        metadata_path=metadata_path,
        metrics=metrics,
        feature_contract_hash=feature_contract_hash,
        training_rows=size,
    )
