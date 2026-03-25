# path: ml/management/commands/train_escalation_model.py
"""Management command to train and register the baseline escalation model."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from ml.features import FEATURE_CONTRACT_VERSION
from ml.reason_codes import REASON_CODE_SCHEMA_VERSION
from ml.services.model_registry import ActiveModelEntry, register_active_model
from ml.training.baseline import train_and_save_baseline_model


class Command(BaseCommand):
    """Train and activate the baseline escalation-risk model."""

    help = "Train the baseline escalation-risk model and register it as active."

    def add_arguments(self, parser: CommandParser) -> None:
        """Register command-line arguments."""

        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--size", type=int, default=500)
        parser.add_argument(
            "--output-dir",
            type=str,
            default=str(Path(settings.BASE_DIR) / "ml_artifacts"),
        )

    def handle(self, *args, **options) -> None:
        """Train the model, persist the artefact, and update the registry."""

        output_dir = Path(options["output_dir"])
        training_output = train_and_save_baseline_model(
            output_dir=output_dir,
            seed=options["seed"],
            size=options["size"],
        )

        registry_path = Path(settings.BASE_DIR) / "ml" / "registry" / "model_registry.json"
        register_active_model(
            registry_path=registry_path,
            entry=ActiveModelEntry(
                version=training_output.model_version,
                model_type="logistic_regression",
                contract_version=FEATURE_CONTRACT_VERSION,
                reason_code_schema_version=REASON_CODE_SCHEMA_VERSION,
                status="active",
            ),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Trained and registered {training_output.model_version}"
            )
        )
