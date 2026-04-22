<!-- path: docs/ml/operations.md -->
# ReturnHub ML Operations

## Purpose

ReturnHub treats escalation-risk scoring as an operational subsystem with named artefacts, documented inputs, and safe degradation rules. The model is useful only when its training, registry, inference contract, and rollback path are all explicit.

## Artefacts and registry

The model registry file shipped in earlier sprints remains the source of truth for which trained artefact is active. Each scored model release should include:

- model identifier
- training timestamp
- feature contract version
- preprocessing version
- label threshold notes
- checksum or hash for the stored artefact

## Inference contract

Inference continues to return the same persisted fields already established in the product contract:

- `score`
- `label`
- `reason_codes`

These fields are stored in `RiskScore` and exposed only in the controlled surfaces defined in the earlier sprints. Ops users should see the signal as triage support, not as an automated final decision.

## Retraining process

A retraining run should:

1. use the deterministic synthetic or approved operational-style dataset path
2. preserve feature ordering and feature contract versioning
3. record the new artefact in the registry
4. run prediction-contract and reproducibility tests before activation

Do not activate a new model artefact if reason-code shape, feature ordering, or output fields drift unexpectedly.

## Rollout and rollback

A rollout should update the active registry entry only after tests pass and the artefact checksum is recorded. A rollback should restore the previous active artefact without changing the persistence schema or the API shape.

## Safe degradation

If scoring fails during inference, the application should continue to support the workflow. The case should remain visible, operational actions should remain available, and the UI should present the risk state as unavailable rather than fabricating a value. Logs should capture the failure details for diagnosis.

## Operational checks

Before a demo or release:

- confirm the active registry entry exists
- confirm prediction-contract tests pass
- confirm the ops queue and case detail pages still render risk safely
- confirm absence of evidence still degrades gracefully for evidence-aware features

## Communication to ops users

Explain the risk signal using consistent language. It is a prioritisation aid based on reproducible signals and stored reason codes. It is not a hidden decision engine and it does not replace the workflow controls already present in the case record.