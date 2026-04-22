<!-- path: docs/ui/visual-regression-checklist.md -->
# ReturnHub Visual Regression Checklist

## Purpose

Use this checklist before demos, release candidates, or major merges that touch templates, CSS, pagination, or HTMX partials. The aim is not pixel-perfect automation. The aim is a disciplined manual pass that catches obvious product regressions before someone else sees them.

## Global shell

- The landing page, login pages, and consoles all use the same typography rhythm and spacing scale.
- Top navigation remains aligned and readable from tablet width upward.
- Flash messages and shared form-error alerts use the same branded visual language and do not overlap page headings or primary actions.
- Keyboard focus is visible on links, buttons, and form fields.

## Ops surface

- `/ops/?page=1` and `/ops/?page=2` both render dense tables without header wrapping that breaks readability.
- Filters, count line, pagination controls, and risk signal presentation remain aligned.
- Empty state and filtered-empty state remain visually distinct from hard-error states.
- Case detail sections preserve hierarchy between summary, actions, notes, events, and documents.

## Customer and merchant surfaces

- Customer and merchant list pages preserve trust and simplicity rather than borrowing the denser ops visual language.
- Upload forms display validation messages inline and keep the action button visible on smaller screens.
- Page 2 remains reachable and styled consistently with page 1.

## Error pages

- 403, 404, and 500 pages match the product shell and offer sensible next actions.
- Error pages do not expose stack traces or framework-default language.
- Recovery actions are keyboard accessible and readable on mobile.

## Responsive review

- Check 375px, 768px, 1024px, and desktop widths.
- Confirm dense customer, merchant, ops, and document tables switch to readable stacked mobile cards on small screens.
- Confirm mobile table labels remain visible and actions remain clear and tappable.
- Confirm stacked actions remain readable and tappable on mobile.

## Accessibility review

- Colour contrast remains acceptable for body text, muted text, badges, and links.
- Headings follow a sensible hierarchy.
- Interactive elements remain reachable by keyboard.
- Informational and error content does not rely on colour alone.
