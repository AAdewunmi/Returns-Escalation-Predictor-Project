<!-- path: docs/api/returns-workflow.md -->
# ReturnHub returns workflow API

Sprint 2 establishes the canonical workflow API for return-case creation and early ops triage.

## Endpoints

`POST /api/returns/`

Creates a return case for the authenticated customer. The request is validated by DRF serializers and persisted through the service layer. Creation emits a `case_created` audit event and persists placeholder risk output.

`GET /api/returns/{id}/`

Returns case detail for the permitted actor. Customers can view only their own cases. Merchants can view only cases tied to their merchant profile. Ops and admins can view all cases.

`PATCH /api/returns/{id}/status/`

Ops and admins can change case status and optional priority through validated service-layer transitions.

`POST /api/returns/{id}/notes/`

Ops and admins can append internal notes. Each note creation emits a `note_added` audit event.

`GET /api/returns/{id}/risk/`

Ops and admins can retrieve persisted risk output. Customers and merchants do not receive this payload.

## Workflow rules

Case creation always starts with deterministic defaults:

- `status = submitted`
- `priority = medium`

Status transitions are validated centrally in the service layer. Views do not mutate model state directly.

## Audit behaviour

The workflow emits append-only `CaseEvent` rows for:

- `case_created`
- `status_updated`
- `note_added`
- `risk_scored`

## Risk visibility

Sprint 2 risk output is intentionally limited to ops and admin users. It is designed as a triage signal and not a customer-facing decision artefact.
