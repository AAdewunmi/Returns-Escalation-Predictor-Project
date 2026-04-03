<!-- path: docs/ui/evidence-states.md -->
# Evidence UI states

Sprint 4 introduces evidence as a reusable product surface. The UI should feel calm, operational, and trustworthy rather than like a generic file-upload widget.

## Primary components

The evidence workspace currently relies on five core components:

- document table
- upload panel
- risk summary
- timeline
- form errors

## State expectations

### Empty evidence state

Use a bordered empty panel with a concise explanation. Do not render empty tables. The message should explain that documents uploaded by customers, merchants, or ops will appear here in created order.

### Upload validation state

Keep validation feedback local to the upload panel. Errors should use semantic alert styling and identify the field causing the problem.

### Success state

Keep the success message local to the upload panel and refresh the document table in place. The current case detail page submits the upload form with `fetch(...)` and swaps only the upload panel and document table fragments from the JSON response.

### Forbidden state

If the actor does not own the case or lacks an upload-capable role, the GET case workspace should render without the upload form and show an “Actor role unavailable” fallback in the panel. Unauthorized upload POST requests should return `403` with refreshed panel HTML, not a generic server error.

### No-risk state

Cases without a risk score should still show the risk panel. Render “No score yet” with explanatory supporting copy so the layout remains stable.

## Responsive notes

The evidence page must stack to a single column on smaller breakpoints. The risk panel should become full width. Tables should retain readability through horizontal scrolling rather than compressing columns into illegible text.
