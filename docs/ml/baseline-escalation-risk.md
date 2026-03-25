path: docs/ml/baseline-escalation-risk.md
# Baseline Escalation Risk Model

## Purpose

Sprint 3 introduces the first working escalation-risk model for ReturnHub. The model is intentionally simple and reproducible. It exists to make the scoring workflow operational, testable, and explainable before later feature expansion.

## Training inputs

The baseline model uses the Sprint 2 feature contract:

- item category
- delivery-to-return time
- return reason
- customer message length
- prior returns count
- order value band
- evidence count

## Data stance

Training uses deterministic synthetic operational rows generated from a seed. No external dataset is required to run tests or train the baseline artefact.

## Model choice

- vectoriser: `DictVectorizer`
- classifier: `LogisticRegression`
- seed-controlled reproducibility
- saved as a versioned `.joblib` artefact

## Artefact outputs

Running the training command writes:

- model artefact file
- metadata JSON file
- updated `ml_artifacts/registry.json`

## Command

```bash
python manage.py train_escalation_model --seed 7 --size 500