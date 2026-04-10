<!-- path: docs/ml/baseline-escalation-risk.md -->
# Baseline Escalation Risk

This document describes the ML flow currently implemented for return-case escalation scoring.

## Current approach

The project uses a logistic-regression baseline with:

- deterministic synthetic training data
- a committed feature contract
- versioned pickle and metadata artifacts
- a committed active-model registry
- persisted `RiskScore` records on return cases

## Feature contract

Training and inference share the feature contract in:

- `ml/contracts/return_case_features.json`
- `ml/features.py`

The current implementation includes signals derived from:

- item category
- delivery-to-return timing
- return reason
- customer message length
- prior returns history
- order-value buckets
- customer evidence activity
- merchant document activity

## Training data

Training data is synthetic and deterministic.

Current dataset flows:

- `ml/datasets/synthetic.py` generates seeded rows
- `ml/datasets/dataset.py` exposes the dataset wrapper
- `ml/management/commands/generate_training_dataset.py` writes CSV output

Default dataset export command:

```bash
docker compose exec -T web python manage.py generate_training_dataset --seed 7 --rows 300
```

Default output path:

```text
artifacts/ml/evidence_aware_training_dataset.csv
```

## Training commands

Baseline training:

```bash
docker compose exec -T web python manage.py train_escalation_model --seed 7 --size 500
```

Retraining wrapper:

```bash
docker compose exec -T web python manage.py retrain_baseline_model --seed 7 --rows 500
```

Current committed active version:

```text
retrain_baseline-logreg-v1-seed-7-rows-500
```

## Artifact layout

Training writes versioned artifacts under:

```text
ml_artifacts/
```

Per model version:

- `<model_version>.pkl`
- `<model_version>.json`

Committed example artifacts currently present:

- `ml_artifacts/retrain_baseline-logreg-v1-seed-7-rows-500.pkl`
- `ml_artifacts/retrain_baseline-logreg-v1-seed-7-rows-500.json`

## Metadata contract

Training metadata currently includes:

- `model_version`
- `feature_contract_version`
- `feature_contract_hash`
- `reason_code_schema_version`
- `training_rows`
- `training_seed`
- `metrics`
- `trained_at`

The inference path requires `feature_contract_hash` to be present in metadata.

## Inference flow

Runtime scoring path:

1. `returns/services/risk.py` requests a scoring result.
2. `ml/services/scoring.py` loads the active registry entry and artifacts.
3. `ml/features.extract_case_features(...)` builds the feature vector.
4. The model returns a probability.
5. The score is quantized to two decimal places.
6. Labels are mapped with current thresholds:
   - `>= 0.75` -> `high`
   - `>= 0.45` -> `medium`
   - otherwise -> `low`
7. Reason codes are generated from the feature vector.
8. The result is persisted as `RiskScore`.

If the active artifact cannot be loaded safely, scoring falls back to the placeholder scorer in `ml/scoring.py`.

## Risk persistence

The returns domain stores one `RiskScore` per case and updates that row on rescore.

Rescoring currently happens on:

- case creation
- status update
- document upload

Each rescore emits a `risk_scored` audit event.

## Dependencies

ML-related runtime packages currently listed in the repository:

- `pandas`
- `scikit-learn`
- `joblib`

## Test coverage

Relevant tests currently cover training, scoring, registry access, artifacts, features, and dataset generation, including:

- `tests/test_baseline_training.py`
- `tests/test_ml_training.py`
- `tests/test_ml_management_commands.py`
- `tests/test_model_registry.py`
- `tests/test_artifact_scoring.py`
- `tests/test_feature_contract.py`
- `tests/test_ml_feature_extraction.py`
- `tests/test_risk_dataset_generation.py`
