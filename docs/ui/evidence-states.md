<!-- path: docs/ui/evidence-states.md -->
# Evidence States

This document describes the document and evidence behavior currently implemented around the shared case detail page and the returns document APIs.

## Current surfaces

Evidence-related UI appears in:

- `/cases/{case_id}/`
- `/ops/{case_id}/`
- `GET /api/returns/{case_id}/documents/`
- `POST /api/returns/{case_id}/documents/`

## Current components

The repository currently uses these evidence-oriented components:

- document table
- upload panel
- risk panel
- timeline
- form error rendering

## Empty state

When no documents are visible for a case:

- the page should render a stable empty state
- the document region should not collapse awkwardly
- copy should make it clear that uploads from permitted actors will appear here

## Upload success state

Server-rendered uploads on `/cases/{case_id}/documents/upload/` currently:

- submit the form asynchronously
- return JSON containing refreshed `upload_panel_html`
- return JSON containing refreshed `document_table_html`
- keep the success message local to the upload panel

Expected success copy in the current flow:

```text
Document uploaded successfully.
```

## Validation and workflow-error state

If form validation fails or the document service rejects the upload:

- the upload panel is re-rendered with local errors
- the surrounding page shell remains intact
- the response uses `400`

## Forbidden state

Current forbidden behaviors:

- unrelated customers or merchants cannot access another actor's case data
- upload attempts without a valid actor role return `403`
- customers can only upload `evidence`
- merchants can only upload `response`

For the API routes, permission failures also return `403` with a structured error payload.

## Visibility state

Document visibility is role-aware:

- ops and admins see all documents for the case
- customers see only documents with `visible_to_customer=True`
- merchants see only documents with `visible_to_merchant=True`

Default visibility on upload:

- `evidence`: customer-visible, merchant-hidden
- `response`: merchant-visible, customer-hidden

## Risk-adjacent state

Evidence uploads trigger a best-effort rescore. On ops-facing surfaces, the risk panel should remain present even when no persisted score exists yet.

Fallback copy expectation:

```text
No score yet
```

## Responsive behavior

Evidence-related layouts should continue to:

- stack to one column on narrow screens
- preserve upload controls and error visibility
- allow document tables to scroll horizontally when needed
