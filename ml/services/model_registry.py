"""Model registry services aligned with the committed ReturnHub registry contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ActiveModelEntry:
    """Single active-model registry entry."""

    version: str
    model_type: str
    contract_version: str
    reason_code_schema_version: str
    status: str


def load_registry(registry_path: Path) -> dict[str, Any]:
    """Load a registry file or return the default active-model structure."""

    if not registry_path.exists():
        return {"active_model": None}

    return json.loads(registry_path.read_text(encoding="utf-8"))


def register_active_model(registry_path: Path, entry: ActiveModelEntry) -> dict[str, Any]:
    """Write the supplied entry as the single active model."""

    registry = {"active_model": asdict(entry)}
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")
    return registry


def get_active_model_entry(registry_path: Path) -> ActiveModelEntry:
    """Return the active model entry from the registry."""

    registry = load_registry(registry_path)
    active = registry.get("active_model")

    if not active:
        raise LookupError("No active model entry found in registry.")

    return ActiveModelEntry(**active)
