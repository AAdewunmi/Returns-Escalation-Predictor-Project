<!-- path: docs/api/ops-queue-contract.md -->
# Ops Queue Contract

This document describes the queue contract shared by the feature-complete server-rendered ops surface at `/ops/` and the DRF queue endpoint at `/api/returns/queue/`.

## Supported query parameters

- `status`
- `priority`
- `risk_label`
- `search`
- `page`

## Accepted values

Statuses:

- `submitted`
- `in_review`
- `waiting_customer`
- `waiting_merchant`
- `approved`
- `rejected`

Priorities:

- `low`
- `medium`
- `high`
- `urgent`

Risk labels:

- `low`
- `medium`
- `high`

Unknown `risk_label` values are normalized away and do not apply a filter.

## Search behavior

`search` is trimmed and applied before pagination. It matches:

- `order_reference`
- customer first name
- customer last name
- customer email
- merchant display name

## Ordering

The queue is built in `returns.services.queue.build_queue_queryset(...)` and ordered explicitly:

1. SLA-breached active cases first
2. higher priority before lower priority
3. earlier `sla_due_at`
4. earlier `created_at`
5. ascending `id`

SLA breach ranking is applied only to active cases in:

- `submitted`
- `in_review`
- `waiting_customer`
- `waiting_merchant`

## Risk annotation

Queue rows do not score cases inline. They annotate each case from the latest persisted `RiskScore` record and expose:

- `current_risk_score`
- `current_risk_label`

If no persisted risk score exists, those fields are `null`.

## Pagination

Shared queue pagination contract:

- query parameter: `page`
- page size: `15`
- missing page: `1`
- non-integer page: `1`
- page `<= 0`: `1`
- out-of-range page in the server-rendered surface resolves to the last page through shared pagination utilities

Pagination links preserve active filters except for `page`.

## Response shape

The API queue response returns:

- `count`
- `next`
- `previous`
- `results`
- `filters`
- `summary`

`filters` echoes:

- `status`
- `priority`
- `risk_label`
- `search`
- `page`

`summary` includes:

- `total`
- `submitted`
- `waiting_customer`
- `waiting_merchant`
- `in_review`
- `approved`
- `rejected`

## Access control

Only authenticated ops and admin users may access the queue API or the `/ops/` queue surface.
