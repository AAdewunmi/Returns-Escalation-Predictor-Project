<!-- path: docs/api/returns-workflow.md -->
# ReturnHub Returns Workflow API

This document describes the current return workflow API for case creation, triage, evidence upload, risk access, and audit export.

## Endpoints

`POST /api/returns/`

Creates a return case for the authenticated customer. The request is validated by DRF serializers and persisted through the service layer. Creation emits a `case_created` audit event and persists risk output through the scoring service.

`GET /api/returns/{id}/`

Returns case detail for the permitted actor. Customers can view only their own cases. Merchants can view only cases tied to their merchant profile. Ops and admins can view all cases.

`PATCH /api/returns/{id}/status/`

Ops and admins can change case status and optional priority through validated service-layer transitions.

`POST /api/returns/{id}/notes/`

Ops and admins can append internal notes. Each note creation emits a `note_added` audit event.

`GET /api/returns/{id}/documents/`

Lists documents visible to the requesting actor under current case-level visibility rules.

`POST /api/returns/{id}/documents/`

Uploads an evidence or response document through the document service, emits a `document_uploaded` event, and triggers a best-effort risk rescore.

`GET /api/returns/{id}/risk/`

Ops and admins can retrieve persisted risk output. Customers and merchants do not receive this payload.

`GET /api/returns/{id}/audit-export/`

Exports case metadata, event history, document metadata, and the latest risk summary as CSV when the audit-export view is enabled.

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
- `document_uploaded`
- `risk_scored`

## Risk visibility

Risk output is intentionally limited to ops and admin users. It is designed as a triage signal and not a customer-facing decision artefact.
