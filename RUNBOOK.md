# ReturnHub Project Runbook

This runbook takes the project from clean clone to a verified current-state local environment. It is written for deterministic setup and manual verification of the implemented product surfaces, API behavior, risk output access controls, and local quality gates.

## Scope

This runbook verifies the following outcomes:

- Docker and PostgreSQL local environment
- Django app boot and migrations
- deterministic demo seed data
- public UI routes
- authenticated console routes
- returns API create, detail, status, notes, and risk behavior
- risk visibility controls for ops, admins, customers, and merchants
- API and ML documentation alignment checks
- lint, formatting, test, and coverage checks

## Prerequisites

Before starting, confirm that the local machine has:

- Git
- Docker
- Docker Compose
- a free local port for `8000`
- a free local port for `5432`

## Repository bootstrap

Clone the repository.

```bash
git clone <your-repo-url> returnhub
```

Expected result:

```text
A local `returnhub/` directory is created.
```

Move into the project directory.

```bash
cd returnhub
```

Expected result:

```text
The shell is now at the repository root.
```

Create the local environment file.

```bash
cp .env.example .env
```

Expected result:

```text
A local `.env` file exists at the repository root.
```

## Start containers

Build and start the application and database containers.

```bash
docker compose up --build -d
```

Expected result:

```text
The `db` and `web` services start successfully in detached mode.
```

Check container status.

```bash
docker compose ps
```

Expected result:

```text
The `db` service is healthy and the `web` service is running.
```

## Apply database migrations

Run migrations.

```bash
docker compose exec -T web python manage.py migrate --noinput
```

Expected result shape:

```text
Operations to perform:
  Apply all migrations: ...
Running migrations:
  No migrations to apply.
```

## Seed deterministic demo data

Run the seed command.

```bash
docker compose exec -T web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

Run the seed command a second time to confirm idempotency.

```bash
docker compose exec -T web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

## Verify demo users and seeded case count

Check the total return case count.

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; print(ReturnCase.objects.count())"
```

Expected result:

```text
32
```

Check that the expected role groups exist.

```bash
docker compose exec -T web python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.order_by('name').values_list('name', flat=True)))"
```

Expected result:

```text
['Admin', 'Customer', 'Merchant', 'Ops']
```

Check the expected local demo usernames.

```bash
docker compose exec -T web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(list(User.objects.order_by('username').values_list('username', flat=True)))"
```

Expected result:

```text
['admin', 'customer', 'merchant', 'ops']
```

## Public route verification

Open the landing page in a browser.

```text
http://127.0.0.1:8000/
```

Expected visible behaviour:

- the page title shows ReturnHub branding
- the landing page headline explains the returns workflow product
- four role entry cards are visible
- buttons exist for Admin, Ops, Customer, and Merchant
- the layout feels branded and not like a default Django page

Open the admin surface entry page.

```text
http://127.0.0.1:8000/login/admin/
```

Expected visible behaviour:

- a branded page loads successfully
- the page explains that the admin entry is reserved and branded
- the page provides a route back to the landing page

Open the ops surface entry page.

```text
http://127.0.0.1:8000/login/ops/
```

Expected visible behaviour:

- a branded page loads successfully
- the page explains that the ops entry is reserved for queue-driven work

Open the customer surface entry page.

```text
http://127.0.0.1:8000/login/customer/
```

Expected visible behaviour:

- a branded page loads successfully
- the page explains that the customer entry is reserved for case tracking

Open the merchant surface entry page.

```text
http://127.0.0.1:8000/login/merchant/
```

Expected visible behaviour:

- a branded page loads successfully
- the page explains that the merchant entry is reserved for linked case responses

## Responsive UI check

Use browser dev tools to test the landing page at smaller widths.

```text
Mobile width example: 390px
Tablet width example: 768px
Desktop width example: 1280px
```

Expected visible behaviour:

- role cards stack cleanly at narrow widths
- navigation remains readable
- primary action buttons remain visible without awkward overlap
- spacing and hierarchy stay coherent

## Pagination contract verification

Check the fallback for out-of-range page numbers using the shared pagination utility.

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), '999').count_line)"
```

Expected result:

```text
Showing 31-32 of 32
```

Check invalid-page fallback.

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), 'banana').page_obj.number)"
```

Expected result:

```text
1
```

Check zero-page fallback.

```bash
docker compose exec -T web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), '0').page_obj.number)"
```

Expected result:

```text
1
```

## Returns API and risk verification

### Create a deterministic case through the real API and persist a linked `RiskScore`

This uses the real `/api/returns/` create path so `RiskScore` is created through the same service-layer persistence flow as the app.

```bash
docker compose exec -T web python manage.py shell <<'PY'
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from accounts.models import MerchantProfile
from returns.models import RiskScore

User = get_user_model()

customer_group = Group.objects.get(name="Customer")
customer_user = User.objects.filter(groups=customer_group).order_by("id").first()
merchant = MerchantProfile.objects.order_by("id").first()

if customer_user is None:
    raise SystemExit("No seeded customer found.")

if merchant is None:
    raise SystemExit("No merchant profile found.")

client = APIClient()
client.force_authenticate(customer_user)

response = client.post(
    "/api/returns/",
    data={
        "merchant_id": str(merchant.pk),
        "external_order_ref": "ORDER-RISK-API-001",
        "item_category": "electronics",
        "return_reason": "damaged",
        "customer_message": "The parcel corner was crushed and the screen is black after power on.",
        "order_value": "950.00",
        "delivery_date": "2026-03-01",
    },
    format="json",
    HTTP_HOST="localhost",
)

print("create_status_code =", response.status_code)

payload = getattr(response, "data", None)
if payload is None:
    print(response.content.decode())
    raise SystemExit("Case creation failed before DRF response rendering.")

print(json.dumps(payload, indent=2, default=str))

if response.status_code != 201:
    raise SystemExit("Case creation failed.")

case_id = str(payload["id"])
risk_exists = RiskScore.objects.filter(case_id=case_id).exists()

print("risk_exists =", risk_exists)

Path("/tmp/returnhub_risk_case_id.txt").write_text(case_id, encoding="utf-8")
Path("/tmp/returnhub_risk_customer_email.txt").write_text(customer_user.email, encoding="utf-8")
PY
```

Expected result shape:

```text
create_status_code = 201
{
  "id": "<case-id>",
  "order_reference": "ORDER-RISK-API-001",
  "status": "submitted",
  "priority": "medium",
  "merchant_name": "<merchant-name>",
  "customer_email": "<seeded-customer-email>",
  "item_category": "electronics",
  "return_reason": "damaged",
  "customer_message": "The parcel corner was crushed and the screen is black after power on.",
  "order_value": "950.00",
  "delivery_date": "2026-03-01",
  "risk": null,
  "created_at": "<timestamp>",
  "updated_at": "<timestamp>"
}
risk_exists = True
```

The create response may include `"risk": null` for the customer-facing caller, which is expected.

### As ops, call `/api/returns/{id}/risk/` and confirm the structured payload returns

```bash
docker compose exec -T web python manage.py shell <<'PY'
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

User = get_user_model()

case_id = Path("/tmp/returnhub_risk_case_id.txt").read_text(encoding="utf-8").strip()

ops_group = Group.objects.get(name="Ops")
ops_user = User.objects.filter(groups=ops_group).order_by("id").first()

if ops_user is None:
    raise SystemExit("No seeded ops user found.")

client = APIClient()
client.force_authenticate(ops_user)

response = client.get(
    f"/api/returns/{case_id}/risk/",
    HTTP_HOST="localhost",
)

print("status_code =", response.status_code)

payload = getattr(response, "data", None)
if payload is None:
    print(response.content.decode())
    raise SystemExit("Risk detail request failed before DRF response rendering.")

print(json.dumps(payload, indent=2, default=str))
PY
```

Expected result shape:

```text
status_code = 200
{
  "model_version": "return-risk-placeholder-v1",
  "score": "<decimal-score>",
  "label": "<low|medium|high>",
  "reason_codes": [
    {
      "code": "<reason-code>",
      "direction": "<up|down>",
      "detail": "<human-readable-detail>"
    }
  ],
  "scored_at": "<timestamp>"
}
```

The exact `score`, `label`, `reason_codes`, and `scored_at` depend on the implemented placeholder scoring and current timestamp, but the response shape should match this contract.

### As the owning customer, call `/api/returns/{id}/` and confirm `risk` is `null`

```bash
docker compose exec -T web python manage.py shell <<'PY'
import json
from pathlib import Path

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

case_id = Path("/tmp/returnhub_risk_case_id.txt").read_text(encoding="utf-8").strip()
customer_email = Path("/tmp/returnhub_risk_customer_email.txt").read_text(encoding="utf-8").strip()

customer_user = User.objects.get(email=customer_email)

client = APIClient()
client.force_authenticate(customer_user)

response = client.get(
    f"/api/returns/{case_id}/",
    HTTP_HOST="localhost",
)

print("status_code =", response.status_code)

payload = getattr(response, "data", None)
if payload is None:
    print(response.content.decode())
    raise SystemExit("Case detail request failed before DRF response rendering.")

print(json.dumps(payload, indent=2, default=str))
print("risk_is_null =", payload.get("risk") is None)
PY
```

Expected result shape:

```text
status_code = 200
{
  "id": "<case-id>",
  "order_reference": "ORDER-RISK-API-001",
  "status": "submitted",
  "priority": "medium",
  "merchant_name": "<merchant-name>",
  "customer_email": "<seeded-customer-email>",
  "item_category": "electronics",
  "return_reason": "damaged",
  "customer_message": "The parcel corner was crushed and the screen is black after power on.",
  "order_value": "950.00",
  "delivery_date": "2026-03-01",
  "risk": null,
  "created_at": "<timestamp>",
  "updated_at": "<timestamp>"
}
risk_is_null = True
```

### Confirm the risk endpoint returns `403` to customers

```bash
docker compose exec -T web python manage.py shell <<'PY'
from pathlib import Path

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

case_id = Path("/tmp/returnhub_risk_case_id.txt").read_text(encoding="utf-8").strip()
customer_email = Path("/tmp/returnhub_risk_customer_email.txt").read_text(encoding="utf-8").strip()

customer_user = User.objects.get(email=customer_email)

client = APIClient()
client.force_authenticate(customer_user)

response = client.get(
    f"/api/returns/{case_id}/risk/",
    HTTP_HOST="localhost",
)

print("status_code =", response.status_code)

payload = getattr(response, "data", None)
if payload is None:
    print(response.content.decode())
    raise SystemExit("Customer risk request failed before DRF response rendering.")

print("response_body =", payload)
PY
```

Expected result:

```text
status_code = 403
response_body = {'detail': 'Only ops and admins can view risk output.'}
```

### Confirm the risk endpoint returns `403` to merchants

```bash
docker compose exec -T web python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from returns.models import ReturnCase

User = get_user_model()

merchant_group = Group.objects.get(name="Merchant")
merchant_user = User.objects.filter(groups=merchant_group).order_by("id").first()
case = ReturnCase.objects.order_by("-created_at").first()

if merchant_user is None:
    raise SystemExit("No seeded merchant user found.")

if case is None:
    raise SystemExit("No case found.")

client = APIClient()
client.force_authenticate(merchant_user)

response = client.get(
    f"/api/returns/{case.pk}/risk/",
    HTTP_HOST="localhost",
)

print("status_code =", response.status_code)

payload = getattr(response, "data", None)
if payload is None:
    print(response.content.decode())
    raise SystemExit("Merchant risk request failed before DRF response rendering.")

print("response_body =", payload)
PY
```

Expected result:

```text
status_code = 403
response_body = {'detail': 'Only ops and admins can view risk output.'}
```

## Console verification

### Open `/console/ops/` and confirm the risk messaging renders above Recent Cases

```bash
docker compose exec -T web python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

User = get_user_model()

ops_group = Group.objects.get(name="Ops")
ops_user = User.objects.filter(groups=ops_group).order_by("id").first()

if ops_user is None:
    raise SystemExit("No seeded ops user found.")

client = Client()
client.force_login(ops_user)

response = client.get("/console/ops/", HTTP_HOST="localhost")
html = response.content.decode()

risk_copy_index = html.find("controlled triage signal")
recent_cases_index = html.find("Recent cases")

print("status_code =", response.status_code)
print("has_risk_copy =", "controlled triage signal" in html)
print("has_ops_only_copy =", "ops only" in html)
print("has_recent_cases =", "Recent cases" in html)
print(
    "risk_copy_before_recent_cases =",
    risk_copy_index != -1 and recent_cases_index != -1 and risk_copy_index < recent_cases_index,
)
PY
```

Expected result:

```text
status_code = 200
has_risk_copy = True
has_ops_only_copy = True
has_recent_cases = True
risk_copy_before_recent_cases = True
```

### Open the other authenticated console routes

These checks confirm that the current role-based console surfaces render successfully for their seeded users.

```bash
docker compose exec -T web python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

users = {
    "admin": User.objects.get(username="admin"),
    "customer": User.objects.get(username="customer"),
    "merchant": User.objects.get(username="merchant"),
}

paths = {
    "admin": "/console/admin/",
    "customer": "/console/customer/",
    "merchant": "/console/merchant/",
}

client = Client()

for role, user in users.items():
    client.force_login(user)
    response = client.get(paths[role], HTTP_HOST="localhost")
    print(role, response.status_code)
    client.logout()
PY
```

Expected result:

```text
admin 200
customer 200
merchant 200
```

## Documentation verification

Read the API and ML docs and confirm endpoint names and registry metadata match committed code.

```bash
docker compose exec -T web python manage.py shell <<'PY'
from pathlib import Path
import json

api_doc = Path("docs/api/returns-workflow.md").read_text(encoding="utf-8")
ml_doc = Path("docs/ml/model-registry.md").read_text(encoding="utf-8")
registry = json.loads(Path("ml/registry/model_registry.json").read_text(encoding="utf-8"))

checks = {
    "api_doc_has_returns_create": "POST /api/returns/" in api_doc,
    "api_doc_has_returns_detail": "GET /api/returns/{id}/" in api_doc,
    "api_doc_has_returns_risk": "GET /api/returns/{id}/risk/" in api_doc,
    "api_doc_omits_stale_analytics_endpoint": "GET /api/analytics/returns/?from=&to=" not in api_doc,
    "ml_doc_has_registry_path": "ml/registry/model_registry.json" in ml_doc,
    "ml_doc_has_placeholder_version": "return-risk-placeholder-v1" in ml_doc,
    "registry_version_matches": registry["active_model"]["version"] == "return-risk-placeholder-v1",
    "registry_model_type_matches": registry["active_model"]["model_type"] == "deterministic_baseline",
    "registry_contract_matches": registry["active_model"]["contract_version"] == "return-risk-sprint2-v1",
}

for key, value in checks.items():
    print(f"{key} = {value}")
PY
```

Expected result:

```text
api_doc_has_returns_create = True
api_doc_has_returns_detail = True
api_doc_has_returns_risk = True
api_doc_omits_stale_analytics_endpoint = True
ml_doc_has_registry_path = True
ml_doc_has_placeholder_version = True
registry_version_matches = True
registry_model_type_matches = True
registry_contract_matches = True
```

## Test verification

Run the full test suite.

```bash
docker compose exec -T web pytest -q
```

Expected result shape:

```text
<all tests pass>
```

Run tests with coverage.

```bash
docker compose exec -T web pytest -q --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

Expected result:

```text
The test suite passes and the total coverage meets or exceeds 80%.
```

## Lint and format verification

Run Ruff.

```bash
docker compose exec -T web python -m ruff check .
```

Expected result:

```text
All checks passed!
```

Run Black format check.

```bash
docker compose exec -T web python -m black . --check
```

Expected result shape:

```text
All done! ✨ 🍰 ✨
<n> files would be left unchanged.
```

## Error page verification

A branded 404 page should render for unknown routes when `DEBUG=False`. This is already covered by tests, but it can also be checked manually in a non-development configuration if needed.

Open an unknown route.

```text
http://127.0.0.1:8000/not-a-real-page/
```

Expected visible behaviour in non-debug mode:

- a branded 404 page renders
- the page uses the shared app shell
- the page provides a clear recovery path back to the landing page

## Current definition of done checklist

The local environment should be considered verified when all items below are true:

- containers build and start successfully
- migrations apply successfully
- demo data seeds successfully
- repeated seeding keeps the case count at `32`
- public UI routes load successfully
- authenticated console routes render successfully for seeded users
- pagination fallback checks return expected results
- returns API create and detail checks pass
- risk endpoint access control behaves correctly for ops, customers, and merchants
- API and ML docs match the committed contracts and registry metadata
- pytest passes
- coverage gate passes
- Ruff passes
- Black check passes

## Clean reset procedure

If local state becomes inconsistent, perform a clean reset.

Stop and remove containers and volumes.

```bash
docker compose down -v
```

Expected result:

```text
Containers stop and local Postgres volume data is removed.
```

Rebuild and restart.

```bash
docker compose up --build -d
```

Expected result:

```text
Fresh containers are created and started.
```

Reapply migrations.

```bash
docker compose exec -T web python manage.py migrate --noinput
```

Expected result:

```text
The database schema is recreated cleanly.
```

Re-seed demo data.

```bash
docker compose exec -T web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

## Troubleshooting

### `web` container exits immediately

Inspect logs.

```bash
docker compose logs web
```

Expected result:

```text
Logs identify the import, dependency, or configuration issue.
```

### Database health check does not pass

Inspect database logs.

```bash
docker compose logs db
```

Expected result:

```text
Logs show whether PostgreSQL startup or credentials are the issue.
```

### Django cannot connect to PostgreSQL

Check that `.env` values match the Compose configuration and confirm that `POSTGRES_HOST=db`.

### `APIClient` calls fail inside `manage.py shell`

If a shell-based API check raises `Invalid HTTP_HOST header: 'testserver'`, rerun the request with `HTTP_HOST="localhost"` as shown in this runbook.

### Tests fail after local experimentation

Use the clean reset procedure, then rerun migrations, seed data, and tests.

## End state

At the end of this runbook, the local environment should be in a verified current-project state with:

- working public pages
- working authenticated console surfaces
- deterministic demo data
- passing returns and risk verification
- documentation aligned with committed contracts
- CI-equivalent local quality checks passing
