# path: tests/test_model_registry.py
"""Tests for ML model registry services."""

from __future__ import annotations

import pytest

from ml.services.model_registry import (
    ActiveModelEntry,
    get_active_model_entry,
    load_registry,
    register_active_model,
)


def test_load_registry_defaults_to_empty_active_model_structure(tmp_path) -> None:
    """Missing registry files should load with the default active-model shape."""

    registry_path = tmp_path / "registry.json"

    assert load_registry(registry_path) == {"active_model": None}


def test_register_active_model_writes_expected_active_model_entry(tmp_path) -> None:
    """Registering a model should replace the single active-model entry."""

    registry_path = tmp_path / "registry.json"

    register_active_model(
        registry_path=registry_path,
        entry=ActiveModelEntry(
            version="baseline-v1",
            model_type="logistic_regression",
            contract_version="return-risk-sprint2-v1",
            reason_code_schema_version="return-risk-reasons-sprint2-v1",
            status="active",
        ),
    )
    register_active_model(
        registry_path=registry_path,
        entry=ActiveModelEntry(
            version="baseline-v2",
            model_type="logistic_regression",
            contract_version="return-risk-sprint2-v1",
            reason_code_schema_version="return-risk-reasons-sprint2-v1",
            status="active",
        ),
    )

    active_entry = get_active_model_entry(registry_path)

    assert active_entry.version == "baseline-v2"
    assert active_entry.model_type == "logistic_regression"
    assert active_entry.status == "active"


def test_get_active_model_entry_raises_when_registry_has_no_active_model(tmp_path) -> None:
    """The service should raise when no active-model payload is present."""

    registry_path = tmp_path / "registry.json"

    with pytest.raises(LookupError, match="No active model entry found in registry."):
        get_active_model_entry(registry_path)
