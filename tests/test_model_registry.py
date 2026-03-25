# path: tests/test_model_registry.py
"""Tests for ML model registry services."""

from __future__ import annotations

from apps.ml.services.model_registry import ModelRegistryEntry, get_active_model_entry, register_model


def test_register_model_marks_latest_entry_active(tmp_path) -> None:
    """The registry should keep only the latest model marked as active."""

    registry_path = tmp_path / "registry.json"

    register_model(
        registry_path=registry_path,
        entry=ModelRegistryEntry(
            model_version="baseline-v1",
            model_path="/tmp/baseline-v1.joblib",
            metadata_path="/tmp/baseline-v1.json",
            feature_contract_hash="hash-v1",
            reason_code_schema_version="v1",
            metrics={"accuracy": 0.82, "roc_auc": 0.90},
            training_rows=100,
            trained_at="2026-03-09T09:00:00+00:00",
            is_active=True,
        ),
    )
    register_model(
        registry_path=registry_path,
        entry=ModelRegistryEntry(
            model_version="baseline-v2",
            model_path="/tmp/baseline-v2.joblib",
            metadata_path="/tmp/baseline-v2.json",
            feature_contract_hash="hash-v1",
            reason_code_schema_version="v1",
            metrics={"accuracy": 0.84, "roc_auc": 0.91},
            training_rows=150,
            trained_at="2026-03-09T10:00:00+00:00",
            is_active=True,
        ),
    )

    active_entry = get_active_model_entry(registry_path)

    assert active_entry.model_version == "baseline-v2"
    assert active_entry.is_active is True
