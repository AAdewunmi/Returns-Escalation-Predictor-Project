<!-- path: docs/ml/model-registry.md -->
# Model Registry

ReturnHub uses a committed JSON registry to point scoring and operational workflows at one active model version.

## Registry file

Path:

```text
ml/registry/model_registry.json
```

Current structure:

```json
{
  "active_model": {
    "contract_version": "return-risk-sprint2-v1",
    "model_type": "logistic_regression",
    "reason_code_schema_version": "return-risk-reasons-sprint3-v1",
    "status": "active",
    "version": "retrain_baseline-logreg-v1-seed-7-rows-500"
  }
}
```

## Current active model

- version: `retrain_baseline-logreg-v1-seed-7-rows-500`
- model type: `logistic_regression`
- contract version: `return-risk-sprint2-v1`
- reason code schema version: `return-risk-reasons-sprint3-v1`
- status: `active`

## How the registry is used

The scoring path in `ml/services/scoring.py`:

- loads the active registry entry
- resolves the expected `.pkl` artifact under `ml_artifacts/`
- resolves the matching metadata `.json`
- rejects loading when the registry, artifact, or metadata is missing or invalid

The returns risk service then uses that scoring result to persist `returns.models.RiskScore`.

## Registry boundaries

The active entry must remain compatible with:

- `ml/contracts/return_case_features.json`
- `ml/features.py`
- `ml/reason_codes.py`
- `ml/services/model_registry.py`
- `ml/services/scoring.py`
- `returns/services/risk.py`

## Update paths

The registry is updated by these commands:

- `python manage.py train_escalation_model --seed 7 --size 500`
- `python manage.py retrain_baseline_model --seed 7 --rows 500`

The standard training command writes an active entry from `train_and_save_baseline_model(...)`.

The retrain wrapper writes an active entry from `ml.training.train.train_and_persist(...)`.

## Operational expectation

Changing the active registry entry should not require API shape changes. The application expects the active model to preserve:

- persisted `RiskScore` fields
- reason-code schema compatibility
- the committed feature-contract boundary
