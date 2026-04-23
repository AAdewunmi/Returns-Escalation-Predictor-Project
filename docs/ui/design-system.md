# ReturnHub Design System

This document describes the design-system baseline represented by the feature-complete templates and styles in `static/css/tokens.css`, `static/css/app.css`, and the shared template partials.

## Product tone

The UI should feel:

- operational
- clear
- trustworthy
- calm under dense workflow content

The codebase favors a server-rendered application shell with reusable partials over isolated one-off page designs.

## Surface types

The UI system supports three surface families:

- public marketing and role-entry pages
- authenticated role dashboards
- workflow pages for customer lists, merchant lists, ops queue, ops case detail, and shared case detail

## Shared shell expectations

The application shell is expected to provide:

- consistent ReturnHub branding
- predictable page titles
- top-level navigation
- flash-message placement near the top of content
- responsive content width and spacing

Template-level shell metadata is provided by `common.context_processors.app_shell`.

## Reusable components in the repository

Current shared partials include patterns for:

- app navigation
- console hero shell
- recent-case cards
- queue summary cards
- queue and filter bars
- status badges
- risk badges
- risk summary panels
- document tables
- upload panels
- notes panels
- note lists and forms
- timelines
- empty states
- pagination
- request-info panels

Ops-specific partials mirror those same patterns for the dedicated `/ops/` surfaces.

## Data-density rules

The completed product surface is intentionally table- and panel-oriented. Design decisions should preserve:

- fast scanning in queue tables
- visible status and priority signals
- stable placement for notes, events, and documents
- local success and validation feedback instead of global page disruption

## State styling rules

- status pills and badges should carry semantic meaning but remain compact
- risk should always be visible as a dedicated panel on ops-facing case detail
- success and validation feedback for uploads should stay in the upload panel
- empty states should explain the absence of data and the next likely action

## Responsive behavior

Current templates are expected to:

- stack multi-column layouts on smaller screens
- keep queue and document tables readable through overflow handling rather than over-compression
- preserve visible headings, action buttons, and status context on mobile widths

## Accessibility baseline

Documentation and templates should continue to assume:

- semantic headings
- visible focus states
- readable color contrast
- keyboard-accessible actions
- text labels instead of color-only meaning
