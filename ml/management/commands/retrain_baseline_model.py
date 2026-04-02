# path: ml/management/commands/retrain_baseline_model.py
"""Management command to retrain and register the baseline ML model."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from ml.training.train import train_and_persist


class Command(BaseCommand):
    """Retrain the baseline model through the current training wrapper."""

    help = "Retrain the baseline model with the seeded evidence-aware dataset flow."

    def add_arguments(self, parser: CommandParser) -> None:
        """Configure command-line arguments."""

        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--rows", type=int, default=500)

    def handle(self, *args, **options) -> None:
        """Retrain the model and print the active version."""

        payload = train_and_persist(
            seed=options["seed"],
            rows=options["rows"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Trained and registered {payload['active_model']['version']}"
            )
        )
