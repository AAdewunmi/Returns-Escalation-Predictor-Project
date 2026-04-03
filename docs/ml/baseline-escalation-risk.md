<!-- path: docs/ml/baseline-escalation-risk.md -->
# Baseline Escalation Risk Model

## Purpose

ReturnHub now has a seeded baseline training flow plus a retraining wrapper for the evidence-aware feature path. The implementation is deterministic so repeated runs with the same seed and row count produce stable training data and model metadata.

## Training inputs

The baseline trainer and inference path share the committed feature contract in `ml/contracts/return_case_features.json`. The current feature set includes:

- item category code
- delivery-to-return days
- return reason code
- damaged-return indicator
- customer message length bucket
- prior returns count
- order value band
- high order-value indicator
- customer evidence count
- hours to first customer evidence
- merchant document count

These features are defined and encoded by:

- `ml/contracts/return_case_features.json`
- `ml/features.py`

## Data stance

Training data is synthetic and deterministic. The training rows are generated
from a random seed in `ml/training/baseline.py`, so repeated runs with the same
inputs produce the same feature rows and labels. `ml/training/train.py` wraps the same trainer and writes a retrain-prefixed model version when the retrain command is used.

No external dataset is required for the baseline training flow.

## Model choice

The current baseline trainer uses:

- `DictVectorizer`
- `LogisticRegression`
- seed-controlled synthetic row generation

The trained artefact is saved as a versioned `.pkl` file.

## Current implementation notes

- The baseline trainer is exposed as a Python function and through Django
  management commands.
- The core training function is `train_and_save_baseline_model(...)` in
  `ml/training/baseline.py`.
- The standard training command is
  `ml/management/commands/train_escalation_model.py`.
- The retrain command is `ml/management/commands/retrain_baseline_model.py`.
- The dataset export command is
  `ml/management/commands/generate_training_dataset.py`.
- The trainer computes a SHA-256 hash of the committed feature contract file and
  stores it in the training metadata.
- `scikit-learn` is imported inside the training function, so importing the
  module itself does not require `sklearn` to be installed.
- Executing training still requires `scikit-learn` to be available in the
  runtime environment.

## Artefact outputs

Running baseline training writes:

- model artefact file: `<model_version>.pkl`
- metadata file: `<model_version>.json`

The metadata currently includes:

- `model_version`
- `feature_contract_version`
- `feature_contract_hash`
- `reason_code_schema_version`
- `training_rows`
- `training_seed`
- `metrics`
- `trained_at`

## Registry behavior

The management command updates the committed active-model registry after a
successful training run.

The command writes the active model entry to:

- `ml/registry/model_registry.json`

The current registry contract stores a single `active_model` object with:

- `version`
- `model_type`
- `contract_version`
- `reason_code_schema_version`
- `status`

Related file locations:

- training module: `ml/training/baseline.py`
- training wrapper: `ml/training/train.py`
- dataset wrapper: `ml/datasets/dataset.py`
- training command: `ml/management/commands/train_escalation_model.py`
- retrain command: `ml/management/commands/retrain_baseline_model.py`
- dataset export command: `ml/management/commands/generate_training_dataset.py`
- registry service: `ml/services/model_registry.py`
- active model registry: `ml/registry/model_registry.json`

## How to run it currently

The baseline trainer can now be run through Django management commands.

Example:

```bash
python manage.py train_escalation_model --seed 7 --size 500
```

Docker equivalent:

```bash
docker compose exec -T web python manage.py train_escalation_model --seed 7 --size 500
```

Retrain wrapper example:

```bash
docker compose exec -T web python manage.py retrain_baseline_model --seed 7 --rows 500
```

Dataset export example:

```bash
docker compose exec -T web python manage.py generate_training_dataset --seed 7 --rows 300
```

The command:

- trains the baseline model
- writes the model artefact and metadata to the configured output directory
- registers the trained model as the active model in
  `ml/registry/model_registry.json`

The retrain command registers a retrain-prefixed version such as
`retrain_baseline-logreg-v1-seed-7-rows-500`.

The trainer is also still available as an importable Python function. A minimal
invocation looks like this:

```bash
python -c "from pathlib import Path; from ml.training.baseline import train_and_save_baseline_model; print(train_and_save_baseline_model(Path('tmp/ml_artifacts')))"
```

## Test coverage

Baseline training coverage currently lives in:

- `tests/test_baseline_training.py`
- `tests/test_ml_training.py`
- `tests/test_ml_management_commands.py`

Those tests validate:

- synthetic row reproducibility
- seed sensitivity
- metadata shape
- stable metadata for repeated runs with the same inputs

Training-dependent test cases skip cleanly when `sklearn` is unavailable in the
runtime container.
