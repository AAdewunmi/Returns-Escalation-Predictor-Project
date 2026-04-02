# path: ml/management/commands/generate_training_dataset.py
"""Management command to generate the pandas training dataset wrapper output."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from ml.datasets.dataset import generate_synthetic_training_dataset


class Command(BaseCommand):
    """Generate a seeded evidence-aware training dataset CSV."""

    help = "Generate the seeded evidence-aware training dataset as CSV."

    def add_arguments(self, parser: CommandParser) -> None:
        """Configure command-line arguments."""

        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--rows", type=int, default=300)
        parser.add_argument(
            "--output",
            type=str,
            default="artifacts/ml/evidence_aware_training_dataset.csv",
        )

    def handle(self, *args, **options) -> None:
        """Generate the DataFrame and write it to CSV."""

        dataset = generate_synthetic_training_dataset(
            seed=options["seed"],
            rows=options["rows"],
        )
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dataset.to_csv(output_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(dataset)} rows to {output_path}"))
