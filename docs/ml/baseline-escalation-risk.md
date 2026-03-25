path: docs/ml/baseline-escalation-risk.md
# Baseline Escalation Risk Model

## Purpose

Sprint 3 introduces the first baseline escalation-risk training flow for ReturnHub.
The implementation is intentionally simple and deterministic so the project can
exercise a reproducible training path before expanding the ML stack further.

## Training inputs

The baseline trainer uses the committed Sprint 2 feature contract. The current
feature set is:

- item category code
- delivery-to-return days
- return reason code
- customer message length bucket
- prior returns count
- order value band

These features are defined and encoded by:

- `ml/contracts/return_case_features.json`
- `ml/features.py`

## Data stance

Training data is synthetic and deterministic. The training rows are generated
from a random seed in `ml/training/baseline.py`, so repeated runs with the same
inputs produce the same feature rows and labels.

No external dataset is required for the baseline training flow.

## Model choice

The current baseline trainer uses:

- `DictVectorizer`
- `LogisticRegression`
- seed-controlled synthetic row generation

The trained artefact is saved as a versioned `.pkl` file.

## Current implementation notes

- The training entry point is the Python function
  `train_and_save_baseline_model(...)` in `ml/training/baseline.py`.
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

The baseline trainer does not currently update the committed model registry
automatically.

Related file locations:

- training module: `ml/training/baseline.py`
- active model registry: `ml/registry/model_registry.json`

## How to run it currently

There is no documented `manage.py train_escalation_model` command in the
current project tree.

The baseline trainer is currently exposed as an importable Python function. A
minimal invocation looks like this:

```bash
python -c "from pathlib import Path; from ml.training.baseline import train_and_save_baseline_model; print(train_and_save_baseline_model(Path('tmp/ml_artifacts')))"
```

## Test coverage

Baseline training coverage currently lives in:

- `tests/test_baseline_training.py`

Those tests validate:

- synthetic row reproducibility
- seed sensitivity
- metadata shape
- stable metadata for repeated runs with the same inputs

Training-dependent test cases skip cleanly when `sklearn` is unavailable in the
runtime container.
