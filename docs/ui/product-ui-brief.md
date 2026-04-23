# ReturnHub Product UI Brief

This brief reflects the product surfaces shipped in the feature-complete ReturnHub baseline.

## Product stance

ReturnHub is not just an API demo. The shipped UI already exposes role-aware workflow surfaces for public entry, dashboards, triage, and case review. The design goal is to make return operations legible without hiding the shared service-layer behavior underneath.

## Current audiences

The repository serves four product audiences:

- admins
- ops users
- customers
- merchants

## Current route map

Public:

- `/`
- `/login/admin/`
- `/login/ops/`
- `/login/customer/`
- `/login/merchant/`

Authenticated dashboards:

- `/console/admin/`
- `/console/ops/`
- `/console/customer/`
- `/console/merchant/`

Workflow pages:

- `/customer/`
- `/customer/{case_id}/`
- `/merchant/`
- `/merchant/{case_id}/`
- `/ops/`
- `/ops/{case_id}/`
- `/cases/{case_id}/`

## Surface intent by audience

Admin:

- monitor overall system activity through the admin console shell
- retain access to Django admin for low-level administration

Ops:

- work from a prioritized queue
- inspect risk, notes, events, and evidence in one case-detail workspace
- update status, request information, and add internal notes inline

Customer:

- browse owned cases through the customer portal
- access only their own cases
- view case detail and visible documents
- upload evidence to their own cases

Merchant:

- browse merchant-linked cases through the merchant portal
- access only merchant-linked cases
- review shared workflow context
- upload response documents to linked cases

## UI priorities

The completed repository emphasizes:

- clear route boundaries by role
- reusable shell structure across pages
- workflow-first layouts over decorative dashboards
- inline partial refresh for ops actions and document uploads
- stable presentation of audit history, evidence, and risk

## UX constraints

- risk is intentionally hidden from customer and merchant detail payloads
- document upload options depend on actor role
- ops queue and case detail must stay useful under dense operational data
- error states should return branded pages or local panel-level validation instead of raw framework output where possible

## Documentation baseline

Future UI documentation should continue to treat these implemented surfaces as the source of truth:

- landing and role-entry pages are real product routes, not placeholders in the docs
- `/customer/` and `/merchant/` are role-bound list portals, not generic dashboards
- `/ops/` and `/ops/{case_id}/` are the main ops workflow surfaces
- `/cases/{case_id}/` is the shared role-aware case workspace
