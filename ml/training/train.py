# path: ml/training/train.py
"""Compatibility training entry point aligned with the current ML stack."""

from __future__ import annotations

import json
from pathlib import Path

from ml.features import FEATURE_CONTRACT_VERSION
from ml.reason_codes import REASON_CODE_SCHEMA_VERSION
from ml.services.model_registry import ActiveModelEntry, register_active_model
from ml.training.baseline import (
    DEFAULT_TRAINING_SEED,
    DEFAULT_TRAINING_SIZE,
    train_and_save_baseline_model,
)

BASE_DIR = Path(__file__).resolve().parents[2]
ARTEFACTS_DIR = BASE_DIR / "ml_artifacts"
REGISTRY_PATH = BASE_DIR / "ml" / "registry" / "model_registry.json"
RETRAIN_VERSION_PREFIX = "retrain_"


def _rename_training_outputs(model_version: str) -> tuple[str, dict[str, object]]:
    """Rename artefacts from the baseline trainer to the retrain-prefixed version."""

    retrain_version = f"{RETRAIN_VERSION_PREFIX}{model_version}"
    original_model_path = ARTEFACTS_DIR / f"{model_version}.pkl"
    original_metadata_path = ARTEFACTS_DIR / f"{model_version}.json"
    retrain_model_path = ARTEFACTS_DIR / f"{retrain_version}.pkl"
    retrain_metadata_path = ARTEFACTS_DIR / f"{retrain_version}.json"

    original_model_path.replace(retrain_model_path)

    metadata = json.loads(original_metadata_path.read_text(encoding="utf-8"))
    metadata["model_version"] = retrain_version
    retrain_metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    original_metadata_path.unlink()

    return retrain_version, metadata


def train_and_persist(
    *,
    seed: int = DEFAULT_TRAINING_SEED,
    rows: int = DEFAULT_TRAINING_SIZE,
) -> dict[str, object]:
    """Train the baseline model, persist artefacts, and register it as active."""

    training_output = train_and_save_baseline_model(
        output_dir=ARTEFACTS_DIR,
        seed=seed,
        size=rows,
    )
    retrain_version, metadata = _rename_training_outputs(training_output.model_version)

    registry = register_active_model(
        registry_path=REGISTRY_PATH,
        entry=ActiveModelEntry(
            version=retrain_version,
            model_type="logistic_regression",
            contract_version=FEATURE_CONTRACT_VERSION,
            reason_code_schema_version=REASON_CODE_SCHEMA_VERSION,
            status="active",
        ),
    )

    return {
        "active_model": registry["active_model"],
        "metadata": metadata,
    }


if __name__ == "__main__":
    train_and_persist()
