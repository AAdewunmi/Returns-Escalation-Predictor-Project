# path: apps/returns/ml/train.py
"""
Training entry point for the evidence-aware escalation model.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from apps.returns.ml.dataset import generate_synthetic_training_dataset
from apps.returns.ml.feature_extraction import load_feature_names

BASE_DIR = Path(__file__).resolve().parent
ARTEFACTS_DIR = BASE_DIR / "artefacts"
REGISTRY_PATH = BASE_DIR / "model_registry.json"
CONTRACT_PATH = BASE_DIR / "feature_contract.json"


def train_and_persist(seed: int = 17) -> dict[str, str]:
    """
    Train the evidence-aware baseline model and persist the artefact and registry.
    """

    ARTEFACTS_DIR.mkdir(parents=True, exist_ok=True)

    feature_names = load_feature_names()
    dataset = generate_synthetic_training_dataset(seed=seed)
    training_frame = dataset[feature_names]
    target = dataset["target"]

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(random_state=seed, max_iter=500)),
        ]
    )
    pipeline.fit(training_frame, target)

    contract_hash = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
    model_version = "sprint4-evidence-aware-v2"
    artefact_path = ARTEFACTS_DIR / f"{model_version}.joblib"

    joblib.dump(
        {
            "pipeline": pipeline,
            "feature_names": feature_names,
            "model_version": model_version,
            "contract_version": "v2",
            "contract_hash": contract_hash,
        },
        artefact_path,
    )

    registry = {
        "active_model_version": model_version,
        "models": [
            {
                "model_version": model_version,
                "contract_version": "v2",
                "contract_hash": contract_hash,
                "artefact_path": str(artefact_path),
                "trained_from": "synthetic_evidence_dataset_seed_17",
            }
        ],
    }
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))

    return registry


if __name__ == "__main__":
    train_and_persist()
