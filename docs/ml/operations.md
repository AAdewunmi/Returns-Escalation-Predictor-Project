<!-- path: docs/ml/operations.md -->
# ReturnHub ML Operations

## Purpose

This document describes the ML operations flow implemented in feature-complete ReturnHub. It covers the active-model registry, the available dataset and training commands, the runtime scoring path, safe fallback behavior, and the concrete checks that can be used before a demo or release.

## Model setup

ReturnHub uses a logistic-regression baseline for escalation-risk scoring.

The live scoring path depends on:

- a committed active-model registry at `ml/registry/model_registry.json`
- versioned model artifacts under `ml_artifacts/`
- the shared feature extraction code in `ml/features.py`
- reason-code generation in `ml/reason_codes.py`
- risk persistence in `returns/services/risk.py`

Committed active registry entry:

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

Committed artifacts:

- `ml_artifacts/retrain_baseline-logreg-v1-seed-7-rows-500.pkl`
- `ml_artifacts/retrain_baseline-logreg-v1-seed-7-rows-500.json`

## Registry contract

The registry stores one active model entry.

The registry shape is defined by:

- `ml/services/model_registry.py`
- `ml/registry.py`

Fields:

- `version`
- `model_type`
- `contract_version`
- `reason_code_schema_version`
- `status`

The registry is updated by:

- `python manage.py train_escalation_model --seed 7 --size 500`
- `python manage.py retrain_baseline_model --seed 7 --rows 500`

`train_escalation_model` writes the active entry directly after baseline training.

`retrain_baseline_model` uses the wrapper flow in `ml/training/train.py` and then writes the active entry.

## Dataset and training commands

Dataset-generation commands:

- `python manage.py generate_risk_dataset --seed 7 --size 250`
- `python manage.py generate_training_dataset --seed 7 --rows 300`

Default dataset outputs:

- `artifacts/ml/synthetic_return_risk_dataset.csv`
- `artifacts/ml/evidence_aware_training_dataset.csv`

Training commands:

- `python manage.py train_escalation_model --seed 7 --size 500`
- `python manage.py retrain_baseline_model --seed 7 --rows 500`

Training artifacts are written under:

- `ml_artifacts/`

Each trained version writes:

- `<model_version>.pkl`
- `<model_version>.json`

## Runtime scoring path

The artifact-backed scoring flow is:

1. `returns/services/risk.py` calls `score_case_and_persist(...)`.
2. That service tries `ml/services/scoring.py`.
3. `ml/services/scoring.py` loads the active registry entry from `ml/registry/model_registry.json`.
4. It resolves the matching `.pkl` and `.json` files under `ml_artifacts/`.
5. It loads the model artifact and metadata.
6. It extracts case features with `ml.features.extract_case_features(...)`.
7. It runs `predict_proba(...)` and converts the probability into:
   - persisted `score`
   - operational `label`
   - structured `reason_codes`
8. `returns/services/risk.py` persists the result to `RiskScore` and writes a `risk_scored` case event.

Current label thresholds in `ml/services/scoring.py`:

- `>= 0.75` -> `high`
- `>= 0.45` -> `medium`
- otherwise -> `low`

The artifact metadata must include `feature_contract_hash`. If it is missing, artifact-backed scoring is rejected.

## Safe degradation

If artifact-backed scoring is unavailable, ReturnHub falls back to the placeholder scorer in `ml/scoring.py`.

This fallback is implemented in:

- `returns/services/risk.py`
- `returns/services/risk_scoring.py`

In the main returns workflow, the active path is `returns/services/risk.py`.

The fallback behavior is:

- the case workflow continues
- a score is still produced from extracted features
- the risk record is persisted
- a warning is logged indicating that placeholder scoring was used

This means the completed baseline does not surface risk as unavailable. It degrades to placeholder scoring instead.

## Rescoring triggers

The returns workflow triggers scoring on:

- case creation in `returns/services/cases.py`
- status update in `returns/services/cases.py`
- document upload in `returns/services/documents.py`

These flows call `returns/services/risk.py:score_case_and_persist(...)`.

## Operational checks

Before a demo or release, the project supports these concrete checks:

- confirm `ml/registry/model_registry.json` contains an active model entry
- confirm the matching `.pkl` and `.json` files exist under `ml_artifacts/`
- run the registry tests in `tests/test_model_registry.py`
- run the artifact scoring and fallback tests in `tests/test_artifact_scoring.py`
- run the training and command tests in:
  - `tests/test_baseline_training.py`
  - `tests/test_ml_training.py`
  - `tests/test_ml_management_commands.py`
  - `tests/test_train_escalation_model_command.py`
  - `tests/test_risk_dataset_generation.py`
- verify the ops queue and case detail surfaces still render risk information safely

## Boundaries

This document describes the completed core implementation.

The core baseline intentionally does not add extra operational metadata such as:

- artifact checksum fields in the registry
- preprocessing-version fields in the registry
- a dedicated rollback management command

Rollback today is a manual operational action: restore a previous valid registry entry and ensure the matching artifacts exist under `ml_artifacts/`.
