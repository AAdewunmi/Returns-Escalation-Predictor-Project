# path: apps/ml/services/model_registry.py
"""Model registry services for ReturnHub ML artefacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelRegistryEntry:
    """Single registry entry describing a trained model artefact."""

    model_version: str
    model_path: str
    metadata_path: str
    feature_contract_hash: str
    reason_code_schema_version: str
    metrics: dict[str, float]
    training_rows: int
    trained_at: str
    is_active: bool = True


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load a model registry file or return the empty default structure."""

    if not registry_path.exists():
        return {"active_model_version": None, "models": []}

    return json.loads(registry_path.read_text())


def register_model(registry_path: Path, entry: ModelRegistryEntry) -> dict[str, Any]:
    """Register a model and mark it as the active version."""

    registry = load_registry(registry_path)

    for model in registry["models"]:
        model["is_active"] = False

    registry["models"].append(asdict(entry))
    registry["active_model_version"] = entry.model_version

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True))
    return registry


def get_active_model_entry(registry_path: Path) -> ModelRegistryEntry:
    """Return the active model entry from the registry."""

    registry = load_registry(registry_path)
    active_model_version = registry.get("active_model_version")

    for row in registry["models"]:
        if row["model_version"] == active_model_version:
            return ModelRegistryEntry(**row)

    raise LookupError("No active model entry found in registry.")
