# ReturnHub Runbook

This runbook takes the project from clean clone to a verified local environment and checks the routes, workflows, APIs, and ML artifacts that currently exist in the repository.

## Scope

This runbook verifies:

- Docker-based local setup with PostgreSQL
- Django migrations and deterministic demo data
- public and authenticated UI routes
- ops queue and ops case-detail workflows
- shared case-detail document upload flow
- returns, documents, queue, risk, audit-export, and analytics APIs
- ML dataset/training commands and committed registry state
- formatting, lint, tests, and coverage gate commands

## Prerequisites

- Git
- Docker
- Docker Compose
- free ports `8000` and `5432`

## Bootstrap

Clone the repository and move into it.

```bash
git clone <your-repo-url> returnhub
cd returnhub
```

Create the local environment file.

```bash
cp .env.example .env
```

Start the containers.

```bash
docker compose up --build -d
docker compose ps
```

Expected result:

- `db` is healthy
- `web` is running

Apply migrations.

```bash
docker compose exec -T web python manage.py migrate --noinput
```

Seed demo data.

```bash
docker compose exec -T web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

Run it again to confirm idempotency.

```bash
docker compose exec -T web python manage.py seed_demo_data
```

## Verify seeded roles and users

Check groups.

```bash
docker compose exec -T web python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.order_by('name').values_list('name', flat=True)))"
```

Expected:

```text
['Admin', 'Customer', 'Merchant', 'Ops']
```

Check users.

```bash
docker compose exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(list(User.objects.order_by('username').values_list('username', flat=True)))"
```

Expected:

```text
['admin', 'customer', 'merchant', 'ops']
```

Shared local password for the seeded users:

```text
password123
```

Check return-case count.

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; print(ReturnCase.objects.count())"
```

Expected baseline:

```text
32
```

## Public route verification

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/login/admin/`
- `http://127.0.0.1:8000/login/ops/`
- `http://127.0.0.1:8000/login/customer/`
- `http://127.0.0.1:8000/login/merchant/`

Expected behavior:

- the landing page presents ReturnHub as a returns workflow product
- each role-entry page renders successfully
- the public shell is branded and responsive

## Authenticated route verification

Log in through the Django admin or shell-created sessions, then open:

- `http://127.0.0.1:8000/console/admin/`
- `http://127.0.0.1:8000/console/ops/`
- `http://127.0.0.1:8000/console/customer/`
- `http://127.0.0.1:8000/console/merchant/`

Expected behavior:

- admin sees total-case context
- ops sees queue summary cards and queue rows
- customer sees recent linked cases
- merchant sees recent linked cases

## Ops queue verification

Open:

```text
http://127.0.0.1:8000/ops/
```

Verify:

- the page loads for `ops` and `admin`
- queue filters accept `status`, `priority`, `risk_label`, `search`, and `page`
- pagination uses a page size of `15`
- invalid pages normalize to page `1`
- summary counts update with filtered results

Check the API equivalent while authenticated as ops or admin:

```text
GET /api/returns/queue/?status=submitted&priority=high&risk_label=medium&search=RH&page=1
```

Expected response shape:

- top-level `count`, `next`, `previous`, `results`
- echoed `filters`
- `summary` with status totals

## Ops case-detail verification

Pick a seeded case ID and open:

```text
http://127.0.0.1:8000/ops/<case_id>/
```

Verify the page renders:

- case header
- status panel
- risk panel
- notes panel
- timeline
- action panel
- evidence list

From the action panel:

- update status to an allowed next state
- request information from customer or merchant
- add an internal note

Expected behavior:

- invalid transitions are rejected
- successful actions refresh the case view
- status changes emit `status_updated`
- notes emit `note_added`

## Shared case-detail and upload verification

Open:

```text
http://127.0.0.1:8000/cases/<case_id>/
```

Verify role-aware behavior:

- ops and admin can view the case and upload either document kind
- the owning customer can view the case and upload only `evidence`
- the linked merchant can view the case and upload only `response`
- unrelated customer or merchant actors should be denied

Upload checks:

- upload a valid JPG or PDF
- confirm the upload panel returns a local success message
- confirm the document table refreshes in place
- confirm a `document_uploaded` event is added

Document visibility checks:

- customers should only see documents marked `visible_to_customer`
- merchants should only see documents marked `visible_to_merchant`
- ops and admins should see all case documents

## API verification

Authenticate with one of the seeded users and verify the live routes.

Create a case as `customer`:

```http
POST /api/returns/
Content-Type: application/json
```

Example payload:

```json
{
  "merchant_id": 1,
  "external_order_ref": "RH-MANUAL-0001",
  "item_category": "electronics",
  "return_reason": "damaged item",
  "customer_message": "Screen arrived cracked.",
  "order_value": "199.99",
  "delivery_date": "2026-01-02"
}
```

Verify:

- response is `201`
- case starts at `status=submitted`
- case starts at `priority=medium`
- a `case_created` event exists
- a `RiskScore` exists for the case

Check detail:

```text
GET /api/returns/<case_id>/
```

Check status update as ops or admin:

```http
PATCH /api/returns/<case_id>/status/
Content-Type: application/json
```

Example payload:

```json
{
  "status": "in_review",
  "priority": "high"
}
```

Check note creation:

```http
POST /api/returns/<case_id>/notes/
Content-Type: application/json
```

Example payload:

```json
{
  "body": "Customer contacted support with photo evidence pending."
}
```

Check documents:

- `GET /api/returns/<case_id>/documents/`
- `POST /api/returns/<case_id>/documents/`

Check risk:

- `GET /api/returns/<case_id>/risk/`

Expected:

- `ops` and `admin` receive risk payloads
- `customer` and `merchant` receive `403`

Check audit export:

- `GET /api/returns/<case_id>/audit-export/`

Expected:

- CSV response
- case rows
- risk rows when a score exists
- event rows
- document metadata rows

Check analytics as ops or admin:

```text
GET /api/analytics/returns/?from=2026-01-01&to=2026-12-31
```

Expected:

- `from`
- `to`
- `total_cases`
- `status_counts`
- `priority_counts`

Also verify that customers cannot access the analytics route.

## ML verification

Check the committed active-model registry.

```bash
docker compose exec -T web python manage.py shell -c "from pathlib import Path; print(Path('ml/registry/model_registry.json').read_text())"
```

Expected current active model metadata:

- version: `retrain_baseline-logreg-v1-seed-7-rows-500`
- model type: `logistic_regression`
- contract version: `return-risk-sprint2-v1`
- reason code schema version: `return-risk-reasons-sprint3-v1`

Generate a dataset:

```bash
docker compose exec -T web python manage.py generate_training_dataset --seed 7 --rows 300
```

Expected output file:

```text
artifacts/ml/evidence_aware_training_dataset.csv
```

Train the baseline model:

```bash
docker compose exec -T web python manage.py train_escalation_model --seed 7 --size 500
```

Retrain through the wrapper flow:

```bash
docker compose exec -T web python manage.py retrain_baseline_model --seed 7 --rows 500
```

Expected outputs under `ml_artifacts/`:

- `<model_version>.pkl`
- `<model_version>.json`

## Quality gates

Run formatting check:

```bash
docker compose exec -T web python -m black . --check
```

Run lint:

```bash
docker compose exec -T web python -m ruff check .
```

Run tests:

```bash
docker compose exec -T web pytest -q
```

Run coverage gate:

```bash
docker compose exec -T web pytest -q --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=85
```

## Convenience targets

Equivalent Make targets:

- `make bootstrap`
- `make up`
- `make down`
- `make ps`
- `make migrate`
- `make test`
- `make test-cov`
- `make lint`
- `make format`
- `make format-check`
- `make check`
