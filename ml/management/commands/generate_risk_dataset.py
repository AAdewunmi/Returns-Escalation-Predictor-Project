# path: apps/ml/management/commands/generate_risk_dataset.py
"""Management command to generate a deterministic synthetic risk dataset."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandParser

from ml.datasets.synthetic import generate_synthetic_rows, write_synthetic_rows_to_csv


class Command(BaseCommand):
    """Generate a CSV dataset for Sprint 3 model training work."""

    help = "Generate deterministic synthetic risk training data for ReturnHub."

    def add_arguments(self, parser: CommandParser) -> None:
        """Configure command-line arguments."""
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--size", type=int, default=250)
        parser.add_argument(
            "--output",
            type=str,
            default="artifacts/ml/synthetic_return_risk_dataset.csv",
        )

    def handle(self, *args, **options) -> None:
        """Generate and write the synthetic dataset."""
        rows = generate_synthetic_rows(seed=options["seed"], size=options["size"])
        output_path = Path(options["output"])
        write_synthetic_rows_to_csv(output_path=output_path, rows=rows)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows)} rows to {output_path}"))
