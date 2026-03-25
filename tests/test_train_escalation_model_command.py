"""Tests for the train_escalation_model management command."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.core.management.base import CommandParser

import ml.management.commands.train_escalation_model as command_module
from ml.features import FEATURE_CONTRACT_VERSION
from ml.management.commands.train_escalation_model import Command
from ml.reason_codes import REASON_CODE_SCHEMA_VERSION
from ml.services.model_registry import ActiveModelEntry
from ml.training.baseline import TrainingOutput


def test_train_escalation_model_command_registers_expected_arguments(settings) -> None:
    """The command should expose the documented defaults for seed, size, and output dir."""

    command = Command()
    parser = CommandParser(prog="manage.py train_escalation_model")

    command.add_arguments(parser)
    options = parser.parse_args([])

    assert options.seed == 7
    assert options.size == 500
    assert options.output_dir == str(Path(settings.BASE_DIR) / "ml_artifacts")


def test_train_escalation_model_command_trains_and_registers_active_model(
    settings, monkeypatch
) -> None:
    """The command should train the model and register it as the active model."""

    command = Command()
    stdout = StringIO()
    command.stdout = stdout
    captured: dict[str, object] = {}

    training_output = TrainingOutput(
        model_version="baseline-logreg-v1-seed-7-rows-120",
        model_path=Path("/tmp/baseline-logreg-v1-seed-7-rows-120.pkl"),
        metadata_path=Path("/tmp/baseline-logreg-v1-seed-7-rows-120.json"),
        metrics={"accuracy": 0.88, "roc_auc": 0.91},
        feature_contract_hash="contract-hash-123",
        training_rows=120,
    )

    def fake_train_and_save_baseline_model(
        output_dir: Path, *, seed: int, size: int
    ) -> TrainingOutput:
        captured["output_dir"] = output_dir
        captured["seed"] = seed
        captured["size"] = size
        return training_output

    def fake_register_active_model(*, registry_path: Path, entry: ActiveModelEntry) -> dict:
        captured["registry_path"] = registry_path
        captured["entry"] = entry
        return {"active_model": {"version": entry.version}}

    monkeypatch.setattr(
        command_module,
        "train_and_save_baseline_model",
        fake_train_and_save_baseline_model,
    )
    monkeypatch.setattr(
        command_module,
        "register_active_model",
        fake_register_active_model,
    )

    command.handle(seed=7, size=120, output_dir="/tmp/ml-artifacts")

    assert captured["output_dir"] == Path("/tmp/ml-artifacts")
    assert captured["seed"] == 7
    assert captured["size"] == 120
    assert captured["registry_path"] == (
        Path(settings.BASE_DIR) / "ml" / "registry" / "model_registry.json"
    )
    assert captured["entry"] == ActiveModelEntry(
        version="baseline-logreg-v1-seed-7-rows-120",
        model_type="logistic_regression",
        contract_version=FEATURE_CONTRACT_VERSION,
        reason_code_schema_version=REASON_CODE_SCHEMA_VERSION,
        status="active",
    )
    assert "Trained and registered baseline-logreg-v1-seed-7-rows-120" in stdout.getvalue()
