# path: tests/test_baseline_training.py
"""Tests for baseline escalation-risk model training."""

from __future__ import annotations

import json

import pytest

from ml.features import FEATURE_CONTRACT_VERSION
from ml.reason_codes import REASON_CODE_SCHEMA_VERSION
from ml.training.baseline import (
    DEFAULT_TRAINING_SEED,
    _get_feature_contract_hash,
    generate_synthetic_training_rows,
    train_and_save_baseline_model,
)


def test_generate_synthetic_training_rows_is_reproducible() -> None:
    """Synthetic training rows should be identical for the same seed and size."""

    first_rows = generate_synthetic_training_rows(seed=11, size=20)
    second_rows = generate_synthetic_training_rows(seed=11, size=20)

    assert first_rows == second_rows
    assert len(first_rows) == 20
    assert all("features" in row for row in first_rows)
    assert all("escalated" in row for row in first_rows)


def test_generate_synthetic_training_rows_changes_when_seed_changes() -> None:
    """Synthetic training rows should differ when the seed changes."""

    first_rows = generate_synthetic_training_rows(seed=11, size=20)
    second_rows = generate_synthetic_training_rows(seed=12, size=20)

    assert first_rows != second_rows


def test_train_and_save_baseline_model_writes_expected_files_and_metadata(tmp_path) -> None:
    """Training should persist both the model artefact and the metadata file."""
    pytest.importorskip("sklearn")

    output = train_and_save_baseline_model(tmp_path, seed=7, size=120)

    assert output.model_path.exists()
    assert output.metadata_path.exists()
    assert output.model_path.suffix == ".pkl"
    assert output.metadata_path.suffix == ".json"
    assert output.training_rows == 120
    assert output.feature_contract_hash == _get_feature_contract_hash()

    metadata = json.loads(output.metadata_path.read_text())

    assert metadata["model_version"] == output.model_version
    assert metadata["feature_contract_version"] == FEATURE_CONTRACT_VERSION
    assert metadata["feature_contract_hash"] == _get_feature_contract_hash()
    assert metadata["reason_code_schema_version"] == REASON_CODE_SCHEMA_VERSION
    assert metadata["training_rows"] == 120
    assert metadata["training_seed"] == 7
    assert "accuracy" in metadata["metrics"]
    assert "roc_auc" in metadata["metrics"]
    assert 0.0 <= metadata["metrics"]["accuracy"] <= 1.0
    assert 0.0 <= metadata["metrics"]["roc_auc"] <= 1.0
    assert "trained_at" in metadata


def test_train_and_save_baseline_model_is_stable_for_same_seed_and_size(tmp_path) -> None:
    """Repeated runs with the same inputs should yield stable metadata apart from timestamps."""
    pytest.importorskip("sklearn")

    first_output = train_and_save_baseline_model(tmp_path / "first", seed=7, size=120)
    second_output = train_and_save_baseline_model(tmp_path / "second", seed=7, size=120)

    first_metadata = json.loads(first_output.metadata_path.read_text())
    second_metadata = json.loads(second_output.metadata_path.read_text())

    # Timestamps are expected to differ between runs, so remove them before
    # comparing the reproducibility-critical metadata fields.
    first_metadata.pop("trained_at")
    second_metadata.pop("trained_at")

    assert first_metadata == second_metadata


@pytest.mark.parametrize(
    ("seed", "size"),
    [
        (DEFAULT_TRAINING_SEED, 50),
        (17, 75),
    ],
)
def test_train_and_save_baseline_model_records_requested_training_shape(
    tmp_path,
    seed: int,
    size: int,
) -> None:
    """Training metadata should reflect the requested seed and row count."""
    pytest.importorskip("sklearn")

    output = train_and_save_baseline_model(tmp_path / f"run-{seed}-{size}", seed=seed, size=size)
    metadata = json.loads(output.metadata_path.read_text())

    assert metadata["training_seed"] == seed
    assert metadata["training_rows"] == size
    assert output.training_rows == size
