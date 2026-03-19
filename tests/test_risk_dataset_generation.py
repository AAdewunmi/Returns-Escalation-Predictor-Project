"""Tests for synthetic ML dataset generation and export."""

from __future__ import annotations

import csv

from ml.datasets.synthetic import generate_synthetic_rows, write_synthetic_rows_to_csv
from ml.management.commands.generate_risk_dataset import Command


def test_generate_synthetic_rows_is_deterministic_for_same_seed() -> None:
    """Synthetic row generation should be repeatable for a fixed seed."""
    first_rows = generate_synthetic_rows(seed=11, size=5)
    second_rows = generate_synthetic_rows(seed=11, size=5)

    assert first_rows == second_rows
    assert len(first_rows) == 5


def test_generate_synthetic_rows_produces_expected_schema_and_labels() -> None:
    """Generated rows should use the documented schema and binary labels."""
    rows = generate_synthetic_rows(seed=3, size=10)
    valid_categories = {"apparel", "electronics", "homeware", "beauty"}
    valid_reasons = {
        "damaged",
        "wrong_item",
        "wrong_size",
        "not_as_described",
        "changed_mind",
    }

    assert all(
        set(row)
        == {
            "item_category",
            "return_reason",
            "delivery_to_return_days",
            "customer_message_length_bucket",
            "prior_returns_count",
            "order_value_band",
            "label",
        }
        for row in rows
    )
    assert all(row["label"] in {0, 1} for row in rows)
    assert all(row["item_category"] in valid_categories for row in rows)
    assert all(row["return_reason"] in valid_reasons for row in rows)


def test_write_synthetic_rows_to_csv_writes_stable_header_order(tmp_path) -> None:
    """CSV export should create parent directories and preserve field ordering."""
    output_path = tmp_path / "artifacts" / "synthetic.csv"
    rows = generate_synthetic_rows(seed=5, size=2)

    write_synthetic_rows_to_csv(output_path=output_path, rows=rows)

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        written_rows = list(reader)

    assert reader.fieldnames == [
        "item_category",
        "return_reason",
        "delivery_to_return_days",
        "customer_message_length_bucket",
        "prior_returns_count",
        "order_value_band",
        "label",
    ]
    assert len(written_rows) == 2
    assert written_rows[0]["item_category"] == rows[0]["item_category"]


def test_generate_risk_dataset_command_writes_requested_output(tmp_path) -> None:
    """Management command should write the requested number of rows to the output path."""
    output_path = tmp_path / "generated" / "risk_dataset.csv"
    command = Command()

    command.handle(seed=9, size=3, output=str(output_path))

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 3
