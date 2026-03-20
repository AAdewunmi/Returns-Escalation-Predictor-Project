<!-- path: docs/ml/model-registry.md -->
# ReturnHub model registry

Sprint 2 introduces a minimal model registry so the scoring contract exists before a trained artefact is added in Sprint 3.

## Registry file

`ml/registry/model_registry.json`

The active entry includes:

- `version`
- `model_type`
- `contract_version`
- `reason_code_schema_version`
- `status`

## Active placeholder entry

Sprint 2 uses `return-risk-placeholder-v1` with `model_type = deterministic_baseline`.

This entry does not represent the final trained model. It exists so the application can:

- persist a stable `RiskScore`
- attach a model version to predictions
- enforce feature contract continuity
- expose structured reason codes to ops users
- prepare the repo for a real training and inference pipeline in Sprint 3

## Contract boundaries

The registry entry must remain compatible with:

- `ml/contracts/return_case_features.json`
- `ml/reason_codes.py`
- `returns/services/risk_scoring.py`

Replacing the placeholder scorer in Sprint 3 should not require changes to the API field names or `RiskScore` persistence shape.
