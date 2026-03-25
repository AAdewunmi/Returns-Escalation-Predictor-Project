# path: apps/ml/management/commands/train_escalation_model.py
"""Management command to train and register the baseline escalation model."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.ml.contracts import REASON_CODE_SCHEMA_VERSION
from apps.ml.services.model_registry import ModelRegistryEntry, register_model
from apps.ml.training.baseline import train_and_save_baseline_model


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
            default=str(Path(settings.BASE_DIR) / "ml_artifacts" / "models"),
        )

    def handle(self, *args, **options) -> None:
        """Train the model, persist the artefact, and update the registry."""

        output_dir = Path(options["output_dir"])
        training_output = train_and_save_baseline_model(
            output_dir=output_dir,
            seed=options["seed"],
            size=options["size"],
        )

        registry_path = Path(settings.BASE_DIR) / "ml_artifacts" / "registry.json"
        register_model(
            registry_path=registry_path,
            entry=ModelRegistryEntry(
                model_version=training_output.model_version,
                model_path=str(training_output.model_path),
                metadata_path=str(training_output.metadata_path),
                feature_contract_hash=training_output.feature_contract_hash,
                reason_code_schema_version=REASON_CODE_SCHEMA_VERSION,
                metrics=training_output.metrics,
                training_rows=training_output.training_rows,
                trained_at=datetime.now(tz=dt_timezone.utc).isoformat(),
                is_active=True,
            ),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Trained and registered {training_output.model_version}"
            )
        )