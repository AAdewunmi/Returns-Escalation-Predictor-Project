# path: apps/ml/registry.py
"""Registry helpers for ReturnHub ML artefacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "registry" / "model_registry.json"


@dataclass(frozen=True)
class ActiveModel:
    """Metadata for the currently active risk model entry."""

    version: str
    model_type: str
    contract_version: str
    reason_code_schema_version: str
    status: str


def load_active_model() -> ActiveModel:
    """Load the active model entry from the committed registry file."""
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    active = payload["active_model"]
    return ActiveModel(
        version=active["version"],
        model_type=active["model_type"],
        contract_version=active["contract_version"],
        reason_code_schema_version=active["reason_code_schema_version"],
        status=active["status"],
    )
