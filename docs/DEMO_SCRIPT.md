<!-- path: docs/DEMO_SCRIPT.md -->
# ReturnHub Demo Script

## Goal

This script provides a deterministic walkthrough of the feature-complete multi-surface ReturnHub product as of April 23, 2026. It is designed for a five to eight minute demo and follows the repo's Docker-based workflow, seeded data, and live routes.

## Pre-demo preparation

Start the application and seed the demo environment.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py seed_returnhub_demo
docker compose exec -T web pytest -q
```

Optional operator checks:

```bash
docker compose ps
docker compose exec -T web python -m ruff check .
docker compose exec -T web python -m black . --check
```

Application URL:

```text
http://127.0.0.1:8000/
```

Seeded demo users:

- `admin.demo`
- `ops.demo`
- `customer.one`
- `customer.two`
- `merchant.one`
- `merchant.two`

Shared local password:

- `ChangeMe123!`

Deterministic case-pick commands:

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; case = ReturnCase.objects.filter(status='submitted').order_by('id').first(); print(f'OPS_CASE_ID={case.id}'); print(f'OPS_CASE_REF={case.order_reference}')"
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; case = ReturnCase.objects.filter(order_reference='RH-RUNBOOK-SPARSE').first() or ReturnCase.objects.order_by('id').first(); print(f'SHARED_CASE_ID={case.id}'); print(f'SHARED_CASE_REF={case.order_reference}')"
```

Use the printed values throughout the demo:

- use `ops.demo` for the ops queue and ops case-detail steps
- use `admin.demo` for the admin console step
- use `customer.one` for the customer console and shared case-detail step
- use `merchant.one` for the merchant console step
- use `OPS_CASE_ID` for the main operational walkthrough
- use `SHARED_CASE_ID` for the shared case-detail walkthrough

## Demo flow

### 1. Open the public product surface

Open:

- `http://127.0.0.1:8000/`

Narration:

- ReturnHub is a Django application for managing return cases across customer, merchant, ops, and admin roles.
- The app combines server-rendered workflow surfaces with DRF APIs, audit events, and persisted escalation-risk scoring.

### 2. Show role entry points

Open:

- `http://127.0.0.1:8000/login/admin/`
- `http://127.0.0.1:8000/login/ops/`
- `http://127.0.0.1:8000/login/customer/`
- `http://127.0.0.1:8000/login/merchant/`

Narration:

- Each role gets a dedicated entry surface.
- The product supports separate operational and self-service journeys without splitting the underlying domain model.

### 3. Show console dashboards

Log in with these seeded users and open:

- `admin.demo` -> `http://127.0.0.1:8000/console/admin/`
- `ops.demo` -> `http://127.0.0.1:8000/console/ops/`
- `customer.one` -> `http://127.0.0.1:8000/console/customer/`
- `merchant.one` -> `http://127.0.0.1:8000/console/merchant/`

Narration:

- Admin sees cross-system oversight.
- Ops sees queue-oriented operational context.
- Customer and merchant consoles show role-specific linked case views.

Optional route callout:

- `customer.one` can also open `http://127.0.0.1:8000/customer/`
- `merchant.one` can also open `http://127.0.0.1:8000/merchant/`
- these list portals provide role-bound case browsing with stable pagination

### 4. Walk through the ops queue

Open:

- log in as `ops.demo`
- open `http://127.0.0.1:8000/ops/`
- locate `OPS_CASE_REF` in the queue

Call out:

- filter inputs for `status`, `priority`, `risk_label`, and free-text search
- summary cards
- queue rows
- stable pagination

Narration:

- The queue is the operational triage surface.
- It supports shared filtering and pagination rules that are also exposed through the API.
- The queue prioritizes active and urgent work rather than behaving like a flat case list.

### 5. Open an ops case-detail workspace

Open the deterministic seeded case:

- `http://127.0.0.1:8000/ops/<OPS_CASE_ID>/`

Call out:

- workflow state panel
- quick navigation
- internal notes
- documents
- timeline
- risk panel
- action panel

Narration:

- This is the main ops workspace.
- Ops users can update status and priority, request more information, and add internal notes from the same case-detail route.
- The page keeps the workflow context, evidence, and audit history together.

### 6. Show inline workflow actions

Using `ops.demo` on `OPS_CASE_ID`:

- change a case from `submitted` to `in_review`
- raise priority if useful for the demo
- add an internal note
- demonstrate a request-for-information action

Narration:

- Workflow actions emit audit events.
- Request-for-information flows move cases into `waiting_customer` or `waiting_merchant`.
- The page is designed as an operational workspace rather than a read-only detail page.

### 7. Show the shared case-detail route

Open:

- log in as `customer.one`
- open `http://127.0.0.1:8000/cases/<SHARED_CASE_ID>/`

Narration:

- This route is shared across roles.
- Visibility and upload permissions are role-aware.
- Customers can upload `evidence`, merchants can upload `response`, and ops/admin can upload either kind.

### 8. Show auditability and risk context

On the case-detail views, call out:

- timeline events
- document list
- risk score panel
- reason-code context when present

Narration:

- ReturnHub keeps workflow changes auditable.
- Uploaded evidence can trigger a best-effort rescore.
- Risk is persisted as part of the case workflow rather than treated as a disconnected model demo.

### 9. Show the live API surface

Use a browser client or API tool and substitute `OPS_CASE_ID` where needed:

- `POST /api/returns/`
- `GET /api/returns/<OPS_CASE_ID>/`
- `PATCH /api/returns/<OPS_CASE_ID>/status/`
- `POST /api/returns/<OPS_CASE_ID>/notes/`
- `GET /api/returns/queue/`
- `GET /api/returns/<OPS_CASE_ID>/documents/`
- `POST /api/returns/<OPS_CASE_ID>/documents/`
- `GET /api/returns/<OPS_CASE_ID>/risk/`
- `GET /api/returns/<OPS_CASE_ID>/audit-export/`
- `GET /api/analytics/returns/?from=YYYY-MM-DD&to=YYYY-MM-DD`

Narration:

- The UI and API are aligned around the same service-layer workflow behavior.
- Analytics are scoped to ops/admin access.
- Audit export provides a portable case record including case, event, risk, and document metadata.

### 10. Close with quality and operational readiness

Show the commands used to validate the repo:

```bash
docker compose exec -T web pytest -q
docker compose exec -T web python -m ruff check .
docker compose exec -T web python -m black . --check
```

Narration:

- The project includes repeatable quality checks and a deterministic demo seed.
- The same repository supports product walkthroughs, operational review, and API verification.

## Time box

Suggested pacing for a five to eight minute walkthrough:

- 1 minute: public landing and role entry points
- 1 minute: console dashboards
- 2 minutes: ops queue and ops case-detail workspace
- 1 minute: workflow actions and audit/risk context
- 1 minute: shared case-detail route
- 1 minute: API surface and quality checks

## Optional proof commands

For a more evidence-driven walkthrough, use the runbook:

- [RUNBOOK.md](../RUNBOOK.md)

The runbook includes:

- seeded data verification
- route verification
- queue and case-detail proof commands
- API checks
- analytics checks
- ML dataset and training commands
- lint, format, test, and coverage verification
