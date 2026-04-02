"""Tests for ML dataset and retraining management commands."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.core.management.base import CommandParser

import ml.management.commands.generate_training_dataset as dataset_command_module
import ml.management.commands.retrain_baseline_model as retrain_command_module
from ml.management.commands.generate_training_dataset import Command as GenerateDatasetCommand
from ml.management.commands.retrain_baseline_model import Command as RetrainCommand


def test_generate_training_dataset_command_registers_expected_arguments() -> None:
    """The dataset command should expose the documented default options."""

    command = GenerateDatasetCommand()
    parser = CommandParser(prog="manage.py generate_training_dataset")

    command.add_arguments(parser)
    options = parser.parse_args([])

    assert options.seed == 7
    assert options.rows == 300
    assert options.output == "artifacts/ml/evidence_aware_training_dataset.csv"


def test_generate_training_dataset_command_writes_requested_output(tmp_path, monkeypatch) -> None:
    """The dataset command should write a CSV through the dataset wrapper."""

    command = GenerateDatasetCommand()
    stdout = StringIO()
    command.stdout = stdout
    captured: dict[str, object] = {}

    class FakeDataset:
        def __len__(self) -> int:
            return 3

        def to_csv(self, output_path: Path, index: bool) -> None:
            captured["output_path"] = output_path
            captured["index"] = index
            output_path.write_text("col\n1\n2\n3\n", encoding="utf-8")

    def fake_generate_synthetic_training_dataset(*, seed: int, rows: int) -> FakeDataset:
        captured["seed"] = seed
        captured["rows"] = rows
        return FakeDataset()

    monkeypatch.setattr(
        dataset_command_module,
        "generate_synthetic_training_dataset",
        fake_generate_synthetic_training_dataset,
    )

    output_path = tmp_path / "artifacts" / "dataset.csv"
    command.handle(seed=17, rows=3, output=str(output_path))

    assert captured["seed"] == 17
    assert captured["rows"] == 3
    assert captured["output_path"] == output_path
    assert captured["index"] is False
    assert output_path.exists()
    assert f"Wrote 3 rows to {output_path}" in stdout.getvalue()


def test_retrain_baseline_model_command_registers_expected_arguments() -> None:
    """The retrain command should expose the documented default options."""

    command = RetrainCommand()
    parser = CommandParser(prog="manage.py retrain_baseline_model")

    command.add_arguments(parser)
    options = parser.parse_args([])

    assert options.seed == 7
    assert options.rows == 500


def test_retrain_baseline_model_command_trains_and_reports_active_version(monkeypatch) -> None:
    """The retrain command should call the wrapper and print the active model version."""

    command = RetrainCommand()
    stdout = StringIO()
    command.stdout = stdout
    captured: dict[str, object] = {}

    def fake_train_and_persist(*, seed: int, rows: int) -> dict[str, object]:
        captured["seed"] = seed
        captured["rows"] = rows
        return {
            "active_model": {
                "version": "retrain_baseline-logreg-v1-seed-17-rows-300",
            },
            "metadata": {},
        }

    monkeypatch.setattr(retrain_command_module, "train_and_persist", fake_train_and_persist)

    command.handle(seed=17, rows=300)

    assert captured["seed"] == 17
    assert captured["rows"] == 300
    assert "Trained and registered retrain_baseline-logreg-v1-seed-17-rows-300" in stdout.getvalue()
