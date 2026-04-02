# path: tests/test_ml_training.py
"""Tests for project-aligned ML dataset and training wrappers."""

from __future__ import annotations

from pathlib import Path

import joblib
import pytest

from ml.training.train import train_and_persist


def test_dataset_wrapper_is_reproducible_with_same_seed() -> None:
    """The pandas dataset wrapper should preserve seeded determinism."""

    pytest.importorskip("pandas")

    from ml.datasets.dataset import generate_synthetic_training_dataset

    first = generate_synthetic_training_dataset(seed=17, rows=12)
    second = generate_synthetic_training_dataset(seed=17, rows=12)

    assert first.equals(second)
    assert "target" in first.columns
    assert "evidence_count" in first.columns


def test_training_wrapper_registers_active_model_and_persists_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The compatibility wrapper should train, write artefacts, and register the result."""

    monkeypatch.setattr("ml.training.train.ARTEFACTS_DIR", tmp_path / "ml_artifacts")
    monkeypatch.setattr(
        "ml.training.train.REGISTRY_PATH",
        tmp_path / "ml" / "registry" / "model_registry.json",
    )

    payload = train_and_persist(seed=17, rows=24)

    version = payload["active_model"]["version"]
    artifact_path = tmp_path / "ml_artifacts" / f"{version}.pkl"
    metadata_path = tmp_path / "ml_artifacts" / f"{version}.json"

    assert payload["active_model"]["model_type"] == "logistic_regression"
    assert artifact_path.exists()
    assert metadata_path.exists()

    model = joblib.load(artifact_path)
    assert hasattr(model, "predict_proba")
    assert payload["metadata"]["training_seed"] == 17
    assert payload["metadata"]["training_rows"] == 24
