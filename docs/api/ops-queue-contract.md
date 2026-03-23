path: docs/api/ops-queue-contract.md
# Ops Queue Contract

## Purpose

This contract defines the intended query, ordering, and pagination behaviour for the ReturnHub ops queue based on the current project schema. It should remain aligned with the shared service-layer contract used by any future API or server-rendered ops queue surface.

## Filters

Supported query parameters:

- `status`
- `priority`
- `risk_label`
- `search`
- `page`

Current status values in the project:

- `submitted`
- `in_review`
- `waiting_customer`
- `waiting_merchant`
- `approved`
- `rejected`

Current priority values in the project:

- `low`
- `medium`
- `high`
- `urgent`

## Ordering rules

Ordering is explicit and stable, and is applied before pagination:

1. SLA-breached cases first
2. Higher priority before lower priority
3. Earlier `sla_due_at` first
4. Earlier `created_at` first
5. `id` as the final tiebreaker

## Search rules

Search is applied before pagination and can match:

- `order_reference`
- customer name
- customer email
- merchant fields exposed by the eventual queue implementation

## Pagination contract

- query parameter: `page`
- page size: `15`
- missing page: page `1`
- invalid or non-integer page: page `1`
- page less than or equal to zero: page `1`

## Filter preservation

Pagination links must preserve all active filters except the page number itself.

## Risk annotation

Queue items read the latest persisted `RiskScore` record for each `ReturnCase` and expose:

- `current_risk_score`
- `current_risk_label`

The queue does not calculate risk inline. It only consumes persisted output from the scoring workflow stored on `returns.models.RiskScore`.
