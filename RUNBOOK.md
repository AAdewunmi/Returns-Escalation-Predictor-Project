# ReturnHub Runbook

This runbook takes the project from clean clone to a verified local environment and checks the routes, workflows, APIs, ML artifacts, and proof commands that match the feature-complete ReturnHub baseline.

## Feature-complete walkthrough intent

This runbook covers the operational commands and checks needed to run, inspect, and verify the completed core ReturnHub product as of April 23, 2026. It is intentionally practical. It assumes a working development or production-like environment and focuses on the tasks an operator, reviewer, or hiring manager might perform during a walkthrough.

Common operator commands:

```bash
make up
make ps
make logs
make shell
make migrate
make test
make test-cov
make lint
make format-check
make check
```

Equivalent Docker Compose commands:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose exec -T web python manage.py migrate
docker compose exec -T web pytest -q
docker compose exec -T web python -m ruff check .
docker compose exec -T web python -m black . --check
```

## Scope

This runbook verifies:

- Docker-based local setup with PostgreSQL
- Django migrations and deterministic demo data
- public and authenticated UI routes
- customer and merchant case-list portals
- ops queue and ops case-detail workflows
- shared case-detail document upload flow
- returns, documents, queue, risk, audit-export, and analytics APIs
- ML dataset and training commands
- formatting, lint, tests, and coverage gate commands
- console-only proof commands suitable for article evidence

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

Set the release identifier returned by `/api/health/` when needed.

- local default: `RELEASE_VERSION=dev`
- staging example: `RELEASE_VERSION=staging-2026-04-21`
- production example: `RELEASE_VERSION=prod-2026-04-21`

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
docker compose exec -T web python manage.py seed_returnhub_demo
```

Expected result:

```text
ReturnHub demo seed complete.
```

Run it again to confirm idempotency.

```bash
docker compose exec -T web python manage.py seed_returnhub_demo
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
['admin.demo', 'customer.one', 'customer.two', 'merchant.one', 'merchant.two', 'ops.demo']
```

Shared local password for the seeded users:

```text
ChangeMe123!
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

Log in with a seeded user, then open:

- `http://127.0.0.1:8000/console/admin/`
- `http://127.0.0.1:8000/console/ops/`
- `http://127.0.0.1:8000/console/customer/`
- `http://127.0.0.1:8000/console/merchant/`

Expected behavior:

- admin sees total-case context
- ops sees queue summary cards and queue rows
- customer sees recent linked cases
- merchant sees recent linked cases

## Customer and merchant portal verification

Open as the matching seeded users:

- `customer.one` -> `http://127.0.0.1:8000/customer/`
- `merchant.one` -> `http://127.0.0.1:8000/merchant/`

Verify:

- list pages render with linked cases only
- pagination uses a page size of `15`
- page 2 remains reachable in the seeded dataset
- detail routes at `/customer/<case_id>/` and `/merchant/<case_id>/` enforce role ownership
- unrelated customer or merchant actors receive a branded `403`

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
- out-of-range pages resolve to the last page
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
- quick navigation
- workflow state panel
- notes panel
- documents panel
- timeline
- risk panel
- action panel
- upload panel

Expected behavior:

- the route is `ops:case-detail`
- the page renders workflow state and ownership context
- the page includes documents, notes, timeline, and risk sections
- sparse cases show stable empty states such as `No documents yet`, `No notes yet`, `No timeline events yet`, and `No score yet`

## Ops actions verification

The ops case-detail page handles inline actions through the same `ops:case-detail` route. It does not use separate `/workflow/`, `/request-info/`, or `/notes/` endpoints.

Supported actions posted to `/ops/<case_id>/`:

- `ops_action=case-update`
- `ops_action=request-info`
- `ops_action=add-note`

Expected behavior:

- valid status updates return `200`
- request-for-information moves the case into `waiting_customer` or `waiting_merchant`
- note creation returns `200`
- invalid submissions return `400` with local panel errors
- unauthorized customer submissions return `403`

Expected event types:

- status changes and request-for-information actions emit `status_updated`
- note creation emits `note_added`

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

Create a case as a seeded customer user such as `customer.one`:

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

- ops and admins receive risk payloads
- customers and merchants receive `403`

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

Expected active model metadata:

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
docker compose exec -T web pytest -q
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

## Proof Commands

These commands are designed for article evidence. They suppress noisy expected error traces by:

- using `Client(HTTP_HOST='localhost', raise_request_exception=False)`
- disabling the `django.request` logger inside the shell command

### Queue verification proof

```bash
docker compose exec web python manage.py shell -c "import logging; from django.test import Client; from django.urls import resolve; from django.contrib.auth import get_user_model; from returns.services.queue import build_queue_queryset, parse_queue_filters; from common.pagination import paginate_queryset; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); client.force_login(user); queryset = build_queue_queryset(parse_queue_filters({})); invalid_page = paginate_queryset(queryset, 'abc').page_obj; zero_page = paginate_queryset(queryset, '0').page_obj; last_page = paginate_queryset(queryset, '999').page_obj; full = client.get('/ops/'); htmx = client.get('/ops/', HTTP_HX_REQUEST='true'); empty = client.get('/ops/?status=closed&priority=high&search=unlikely_runbook_value'); full_content = full.content.decode(); htmx_content = htmx.content.decode(); empty_content = empty.content.decode(); print('OPS_QUEUE_URL=/ops/'); print('OPS_QUEUE_VIEW=ops:queue'); print(f'OPS_QUEUE_ROUTE_CHECK={resolve(\"/ops/\").view_name == \"ops:queue\"}'); print(f'OPS_QUEUE_PAGE_RENDER_CHECK={full.status_code == 200 and \"Returns queue\" in full_content}'); print(f'OPS_QUEUE_PAGINATION_CHECK={invalid_page.number == 1 and zero_page.number == 1 and last_page.number == last_page.paginator.num_pages}'); print(f'OPS_QUEUE_HTMX_PARTIAL_CHECK={htmx.status_code == 200 and \"Return cases\" in htmx_content and \"Showing\" in htmx_content}'); print(f'OPS_QUEUE_EMPTY_STATE_CHECK={\"No cases match these filters\" in empty_content}')"
```

### Case detail verification proof

```bash
docker compose exec web python manage.py shell -c "import logging; from django.test import Client; from django.urls import reverse, resolve; from django.contrib.auth import get_user_model; from returns.models import ReturnCase; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); case = ReturnCase.objects.order_by('id').first(); sparse_case = ReturnCase.objects.filter(documents__isnull=True, risk_score__isnull=True, notes__isnull=True, events__isnull=True).distinct().first() or case; client.force_login(user); response = client.get(reverse('ops:case-detail', args=[case.pk])); sparse_response = client.get(reverse('ops:case-detail', args=[sparse_case.pk])); content = response.content.decode(); sparse_content = sparse_response.content.decode(); print(f'CASE_ID={case.pk}'); print(f'CASE_REFERENCE={case.order_reference}'); print(f'OPS_CASE_DETAIL_URL={reverse(\"ops:case-detail\", args=[case.pk])}'); print('OPS_CASE_DETAIL_VIEW=ops:case-detail'); print(f'OPS_CASE_DETAIL_ROUTE_CHECK={resolve(reverse(\"ops:case-detail\", args=[case.pk])).view_name == \"ops:case-detail\"}'); print(f'OPS_CASE_DETAIL_PAGE_RENDER_CHECK={response.status_code == 200}'); print(f'OPS_CASE_DETAIL_WORKFLOW_STATE_CHECK={\"Workflow state\" in content}'); print(f'OPS_CASE_DETAIL_DOCUMENTS_SECTION_CHECK={(\"Documents\" in content) or (\"Evidence\" in content)}'); print(f'OPS_CASE_DETAIL_TIMELINE_SECTION_CHECK={\"Audit timeline\" in content}'); print(f'OPS_CASE_DETAIL_RISK_PANEL_CHECK={\"Escalation risk\" in content}'); print(f'OPS_CASE_DETAIL_EMPTY_DOCUMENTS_CHECK={\"No documents yet\" in sparse_content}'); print(f'OPS_CASE_DETAIL_EMPTY_RISK_CHECK={\"No score yet\" in sparse_content}')"
```

### Workflow action proof

```bash
docker compose exec web python manage.py shell -c "import logging; from django.test import Client; from django.contrib.auth import get_user_model; from returns.models import ReturnCase, CaseEvent, CaseNote; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); ops_user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); customer_user = User.objects.filter(groups__name__iexact='Customer').first(); update_case = ReturnCase.objects.filter(status='submitted').order_by('id').first() or ReturnCase.objects.order_by('id').first(); request_case = ReturnCase.objects.filter(status='submitted').exclude(pk=update_case.pk).order_by('id').first() or update_case; note_case = ReturnCase.objects.exclude(pk__in=[update_case.pk, request_case.pk]).order_by('id').first() or update_case; invalid_case = ReturnCase.objects.filter(status='approved').order_by('id').first() or update_case; client.force_login(ops_user); workflow_response = client.post(f'/ops/{update_case.pk}/', {'ops_action': 'case-update', 'status': 'in_review', 'priority': 'high'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); update_case.refresh_from_db(); workflow_event = CaseEvent.objects.filter(return_case=update_case, event_type='status_updated', payload__new_status='in_review').exists(); request_response = client.post(f'/ops/{request_case.pk}/', {'ops_action': 'request-info', 'recipient': 'customer', 'message': 'Please upload a clearer image of the damaged item.'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); request_case.refresh_from_db(); request_event = CaseEvent.objects.filter(return_case=request_case, event_type='status_updated', payload__note__icontains='Requested additional information from customer').exists(); note_body = 'Customer appears responsive. Await merchant packaging confirmation.'; note_response = client.post(f'/ops/{note_case.pk}/', {'ops_action': 'add-note', 'body': note_body}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); note_event = CaseEvent.objects.filter(return_case=note_case, event_type='note_added').exists(); note_saved = CaseNote.objects.filter(return_case=note_case, body=note_body).exists(); invalid_response = client.post(f'/ops/{invalid_case.pk}/', {'ops_action': 'case-update', 'status': '', 'priority': ''}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); invalid_html = invalid_response.json().get('action_panel_html', ''); client.force_login(customer_user); wrong_role_response = client.post(f'/ops/{note_case.pk}/', {'ops_action': 'add-note', 'body': 'Unauthorised note attempt'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); print(f'OPS_WORKFLOW_UPDATE_CHECK={workflow_response.status_code == 200 and update_case.status == \"in_review\" and update_case.priority == \"high\" and workflow_event}'); print(f'OPS_REQUEST_INFO_CHECK={request_response.status_code == 200 and request_case.status == \"waiting_customer\" and request_event}'); print(f'OPS_ADD_NOTE_CHECK={note_response.status_code == 200 and note_saved and note_event}'); print(f'OPS_INVALID_WORKFLOW_CHECK={invalid_response.status_code == 400}'); print(f'OPS_INVALID_WORKFLOW_ERROR_CHECK={\"This field is required.\" in invalid_html}'); print(f'OPS_ACTION_WRONG_ROLE_CHECK={wrong_role_response.status_code == 403}')"
```

### Layout verification proof

```bash
docker compose exec web python manage.py shell -c "import logging; from django.test import Client; from django.contrib.auth import get_user_model; from returns.models import ReturnCase, CaseNote; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); nav_case = ReturnCase.objects.order_by('id').first(); sparse_case = ReturnCase.objects.exclude(pk=nav_case.pk).order_by('id').first() or nav_case; CaseNote.objects.filter(return_case=nav_case).delete(); CaseNote.objects.filter(return_case=sparse_case).delete(); CaseNote.objects.create(return_case=nav_case, author=user, body='Older note for ordering check'); CaseNote.objects.create(return_case=nav_case, author=user, body='Newer note for ordering check'); client.force_login(user); response = client.get(f'/ops/{nav_case.pk}/'); sparse_response = client.get(f'/ops/{sparse_case.pk}/'); content = response.content.decode(); sparse_content = sparse_response.content.decode(); print(f'OPS_CASE_DETAIL_QUICK_NAVIGATION_CHECK={\"Quick navigation\" in content}'); print(f'OPS_ACTION_BAR_WORKFLOW_LINK_CHECK={\"#case-status-panel\" in content}'); print(f'OPS_ACTION_BAR_NOTES_LINK_CHECK={\"#case-notes-panel\" in content}'); print(f'OPS_ACTION_BAR_DOCUMENTS_LINK_CHECK={\"#case-document-table\" in content}'); print(f'OPS_ACTION_BAR_TIMELINE_LINK_CHECK={\"#case-timeline\" in content}'); print(f'OPS_CASE_DETAIL_NOTES_PLACEMENT_CHECK={content.index(\"Workflow state\") < content.index(\"Internal notes\") < content.index(\"Documents\")}'); print(f'OPS_NOTES_ORDERING_RENDER_CHECK={content.index(\"Newer note for ordering check\") < content.index(\"Older note for ordering check\")}'); print(f'OPS_EMPTY_NOTES_CHECK={\"No notes yet\" in sparse_content}')"
```

### Ops surface proof

```bash
docker compose exec web python manage.py shell -c "import logging; from django.test import Client; from django.contrib.auth import get_user_model; from returns.models import ReturnCase; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); first_case = ReturnCase.objects.order_by('id').first(); sparse_case = ReturnCase.objects.filter(order_reference='RH-RUNBOOK-SPARSE').first() or first_case; client.force_login(user); queue = client.get('/ops/'); detail = client.get(f'/ops/{first_case.pk}/'); page_two = client.get('/ops/?page=2'); empty = client.get('/ops/?status=closed&priority=high&search=unlikely_runbook_value'); sparse = client.get(f'/ops/{sparse_case.pk}/'); queue_content = queue.content.decode(); detail_content = detail.content.decode(); empty_content = empty.content.decode(); sparse_content = sparse.content.decode(); print(f'OPS_QUEUE_SMOKE_RENDER_CHECK={queue.status_code == 200 and \"Returns queue\" in queue_content}'); print(f'OPS_DETAIL_SMOKE_RENDER_CHECK={detail.status_code == 200 and first_case.order_reference in detail_content}'); print(f'OPS_QUEUE_PAGE_TWO_CHECK={page_two.status_code == 200 and \"Showing 16-\" in page_two.content.decode()}'); print(f'OPS_QUEUE_EMPTY_STATE_CHECK={\"No cases match these filters\" in empty_content}'); print(f'OPS_DETAIL_EMPTY_DOCUMENTS_CHECK={\"No documents yet\" in sparse_content}'); print(f'OPS_DETAIL_EMPTY_TIMELINE_CHECK={\"No timeline events yet\" in sparse_content}'); print(f'OPS_DETAIL_LOADING_LAYER_CHECK={(\"data-loading-label\" in detail_content) and (\"rh-fragment-panel__status\" in detail_content)}'); print(f'OPS_DETAIL_FRAGMENT_IDS_CHECK={(\"case-status-panel\" in detail_content) and (\"case-notes-panel\" in detail_content)}')"
```

### Compact console proof

```bash
bash -lc "docker compose exec web pytest -q tests/test_ops_queue.py tests/test_ops_case_detail.py tests/test_ops_console.py tests/test_console_shell.py tests/test_case_detail_empty_states.py tests/test_ops_queue_api.py && docker compose exec web python -m ruff check . && docker compose exec web python -m black . --check && docker compose exec web python manage.py shell -c \"import logging; from django.test import Client; from django.urls import resolve, reverse; from django.contrib.auth import get_user_model; from returns.models import ReturnCase, CaseEvent, CaseNote; logging.getLogger('django.request').disabled = True; User = get_user_model(); client = Client(HTTP_HOST='localhost', raise_request_exception=False); ops_user = User.objects.filter(groups__name__iexact='Ops').first() or User.objects.filter(is_superuser=True).first(); customer_user = User.objects.filter(groups__name__iexact='Customer').first(); queue_case = ReturnCase.objects.filter(status='submitted').order_by('id').first() or ReturnCase.objects.order_by('id').first(); request_case = ReturnCase.objects.filter(status='submitted').exclude(pk=queue_case.pk).order_by('id').first() or queue_case; note_case = ReturnCase.objects.exclude(pk__in=[queue_case.pk, request_case.pk]).order_by('id').first() or queue_case; client.force_login(ops_user); queue = client.get('/ops/'); detail = client.get(f'/ops/{queue_case.pk}/'); page_two = client.get('/ops/?page=2'); empty = client.get('/ops/?status=closed&priority=high&search=unlikely_runbook_value'); workflow = client.post(f'/ops/{queue_case.pk}/', {'ops_action': 'case-update', 'status': 'in_review', 'priority': 'high'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); queue_case.refresh_from_db(); request_info = client.post(f'/ops/{request_case.pk}/', {'ops_action': 'request-info', 'recipient': 'customer', 'message': 'Please upload a clearer image of the damaged item.'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); note_body = 'Compact proof note'; add_note = client.post(f'/ops/{note_case.pk}/', {'ops_action': 'add-note', 'body': note_body}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); CaseNote.objects.filter(return_case=queue_case).delete(); CaseNote.objects.create(return_case=queue_case, author=ops_user, body='Older compact proof note'); CaseNote.objects.create(return_case=queue_case, author=ops_user, body='Newer compact proof note'); detail_after = client.get(f'/ops/{queue_case.pk}/'); sparse_case = ReturnCase.objects.filter(order_reference='RH-RUNBOOK-SPARSE').first() or queue_case; sparse = client.get(f'/ops/{sparse_case.pk}/'); client.force_login(customer_user); wrong_role = client.post(f'/ops/{note_case.pk}/', {'ops_action': 'add-note', 'body': 'Unauthorised note attempt'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest'); detail_content = detail_after.content.decode(); sparse_content = sparse.content.decode(); empty_content = empty.content.decode(); print(f'OPS_QUEUE_ROUTE_CHECK={resolve(\\\"/ops/\\\").view_name == \\\"ops:queue\\\"}'); print(f'OPS_QUEUE_PAGE_RENDER_CHECK={queue.status_code == 200}'); print(f'OPS_CASE_DETAIL_ROUTE_CHECK={resolve(reverse(\\\"ops:case-detail\\\", args=[queue_case.pk])).view_name == \\\"ops:case-detail\\\"}'); print(f'OPS_CASE_DETAIL_PAGE_RENDER_CHECK={detail.status_code == 200}'); print(f'OPS_WORKFLOW_UPDATE_CHECK={workflow.status_code == 200 and queue_case.status == \\\"in_review\\\" and queue_case.priority == \\\"high\\\" and CaseEvent.objects.filter(return_case=queue_case, event_type=\\\"status_updated\\\", payload__new_status=\\\"in_review\\\").exists()}'); print(f'OPS_REQUEST_INFO_CHECK={request_info.status_code == 200 and CaseEvent.objects.filter(return_case=request_case, event_type=\\\"status_updated\\\", payload__note__icontains=\\\"Requested additional information from customer\\\").exists()}'); print(f'OPS_ADD_NOTE_CHECK={add_note.status_code == 200 and CaseNote.objects.filter(return_case=note_case, body=note_body).exists() and CaseEvent.objects.filter(return_case=note_case, event_type=\\\"note_added\\\").exists()}'); print(f'OPS_NOTES_ORDERING_RENDER_CHECK={detail_content.index(\\\"Newer compact proof note\\\") < detail_content.index(\\\"Older compact proof note\\\")}'); print(f'OPS_QUEUE_PAGE_TWO_CHECK={page_two.status_code == 200 and \\\"Showing 16-\\\" in page_two.content.decode()}'); print(f'OPS_QUEUE_EMPTY_STATE_CHECK={\\\"No cases match these filters\\\" in empty_content}'); print(f'OPS_DETAIL_EMPTY_DOCUMENTS_CHECK={\\\"No documents yet\\\" in sparse_content}'); print(f'OPS_DETAIL_EMPTY_TIMELINE_CHECK={\\\"No timeline events yet\\\" in sparse_content}'); print(f'OPS_ACTION_WRONG_ROLE_CHECK={wrong_role.status_code == 403}')\""
```
