# path: apps/returns/tests/test_ml_training.py
"""
Tests for deterministic evidence-aware training.
"""

from __future__ import annotations

from pathlib import Path

import joblib

from apps.returns.ml.train import train_and_persist


def test_training_is_reproducible_with_same_seed(tmp_path: Path, monkeypatch):
    """
    Training with the same seed should produce the same probability for the same row.
    """

    monkeypatch.setattr("apps.returns.ml.train.ARTEFACTS_DIR", tmp_path / "artefacts")
    monkeypatch.setattr("apps.returns.ml.train.REGISTRY_PATH", tmp_path / "model_registry.json")

    first_registry = train_and_persist(seed=17)
    second_registry = train_and_persist(seed=17)

    first_artefact = joblib.load(first_registry["models"][0]["artefact_path"])
    second_artefact = joblib.load(second_registry["models"][0]["artefact_path"])

    row = [[1, 0, 0, 1, 0, 0, 4, 120, 2, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0]]
    first_probability = float(first_artefact["pipeline"].predict_proba(row)[0][1])
    second_probability = float(second_artefact["pipeline"].predict_proba(row)[0][1])

    assert round(first_probability, 6) == round(second_probability, 6)
