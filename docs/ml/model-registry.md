<!-- path: docs/ml/model-registry.md -->
# ReturnHub Model Registry

ReturnHub uses a committed model registry so scoring can resolve the active model version and validate contract metadata consistently.

## Registry file

`ml/registry/model_registry.json`

The active entry includes:

- `version`
- `model_type`
- `contract_version`
- `reason_code_schema_version`
- `status`

## Active model entry

The current active entry is artifact-backed and points at a logistic-regression baseline, for example `retrain_baseline-logreg-v1-seed-7-rows-500` with `model_type = logistic_regression`.

This entry exists so the application can:

- persist a stable `RiskScore`
- attach a model version to predictions
- enforce feature contract continuity
- expose structured reason codes to ops users
- preserve one explicit model pointer for inference and retraining workflows

## Contract boundaries

The registry entry must remain compatible with:

- `ml/contracts/return_case_features.json`
- `ml/reason_codes.py`
- `ml/services/model_registry.py`
- `ml/services/scoring.py`
- `returns/services/risk.py`

Updating the active model version should not require changes to the API field names or `RiskScore` persistence shape.
