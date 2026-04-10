<!-- path: docs/api/returns-workflow.md -->
# Returns Workflow API

This document describes the return-case API behavior implemented in the current repository.

## Runtime routes

The live application exposes these routes:

- `POST /api/returns/`
- `GET /api/returns/{case_id}/`
- `PATCH /api/returns/{case_id}/status/`
- `POST /api/returns/{case_id}/notes/`
- `GET /api/returns/queue/`
- `GET /api/returns/{case_id}/documents/`
- `POST /api/returns/{case_id}/documents/`
- `GET /api/returns/{case_id}/risk/`
- `GET /api/returns/{case_id}/audit-export/`

The repository also contains compatibility wrappers in `api/` and canonical route modules in `returns/api/`; both are aligned around the same workflow services.

## Create case

`POST /api/returns/`

Current request fields:

- `merchant_id`
- `external_order_ref`
- `item_category`
- `return_reason`
- `customer_message`
- `order_value`
- `delivery_date`

Rules:

- only authenticated customers and admins may create cases
- `order_value` must be greater than zero
- `delivery_date` cannot be in the future
- `customer_message` cannot be blank after trimming

Current defaults on create:

- `status = submitted`
- `priority = medium`

Side effects:

- SLA fields are refreshed
- `case_created` audit event is emitted
- risk is scored and persisted

## Retrieve case detail

`GET /api/returns/{case_id}/`

Access rules:

- ops and admins can view any case
- customers can view only their own cases
- merchants can view only cases tied to their merchant profile

Response includes:

- core case fields
- embedded document metadata
- `risk`
- `latest_risk`

Risk visibility in the detail serializer:

- ops/admin: populated when a `RiskScore` exists
- customer/merchant: `null`

## Update status

`PATCH /api/returns/{case_id}/status/`

Allowed for:

- ops
- admin

Request fields:

- `status`
- `priority` optional

Allowed status transitions:

- `submitted -> in_review | waiting_customer | waiting_merchant | approved | rejected`
- `in_review -> waiting_customer | waiting_merchant | approved | rejected`
- `waiting_customer -> in_review | approved | rejected`
- `waiting_merchant -> in_review | approved | rejected`
- `approved ->` no further transitions
- `rejected ->` no further transitions

Side effects:

- `last_status_changed_at` is updated
- SLA fields are refreshed
- optional priority update is persisted
- `status_updated` audit event is emitted
- risk is rescored and persisted

## Add note

`POST /api/returns/{case_id}/notes/`

Allowed for:

- ops
- admin

Request field:

- `body`

Rules:

- body cannot be blank after trimming

Side effect:

- `note_added` audit event is emitted

## Queue

`GET /api/returns/queue/`

Allowed for:

- ops
- admin

Supports:

- filtering by `status`, `priority`, `risk_label`, `search`, `page`
- explicit ordering
- shared pagination
- summary counts

See `docs/api/ops-queue-contract.md` for the full queue contract.

## Documents

`GET /api/returns/{case_id}/documents/`

Returns documents visible to the requesting actor.

Visibility rules:

- ops/admin see all documents
- owning customer sees only documents with `visible_to_customer=True`
- linked merchant sees only documents with `visible_to_merchant=True`

`POST /api/returns/{case_id}/documents/`

Upload rules:

- customers can upload only `evidence` to their own cases
- merchants can upload only `response` to their own cases
- ops/admin can upload either document kind

Side effects:

- `EvidenceDocument` metadata is persisted
- `document_uploaded` audit event is emitted
- best-effort rescoring runs after upload

Visibility defaults:

- `evidence` defaults to customer-visible and merchant-hidden
- `response` defaults to merchant-visible and customer-hidden

## Risk

`GET /api/returns/{case_id}/risk/`

Allowed for:

- ops
- admin

Behavior:

- returns persisted `RiskScore`
- returns `404` when no score exists yet
- returns `403` for customers and merchants

Current response fields:

- `model_version`
- `score`
- `label`
- `reason_codes`
- `scored_at`

## Audit export

`GET /api/returns/{case_id}/audit-export/`

Returns CSV export content for an accessible case, including:

- case metadata rows
- latest risk rows when present
- event history rows
- document metadata rows

## Audit events emitted today

- `case_created`
- `status_updated`
- `note_added`
- `document_uploaded`
- `risk_scored`

Seeded demo data also emits:

- `seed_case_created`
