# ReturnHub: Online Retailer Returns Escalation Platform

![CI Pipeline](https://img.shields.io/badge/CI-GitHub_Actions-blue)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Coverage](https://img.shields.io/badge/coverage-gated-brightgreen)
![Code Style](https://img.shields.io/badge/code_style-black-black)
![Lint](https://img.shields.io/badge/lint-ruff-2ea44f)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-5.x-0c4b33)
![Docker](https://img.shields.io/badge/docker-compose-2496ed)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

ReturnHub is a Django application for online retailer returns and customer support. It is designed as an API-first workflow product with server-rendered UI surfaces for ops teams, customers, merchants, and administrators. The system centralises return cases, evidence, notes, audit events, analytics, and placeholder escalation-risk scoring behind shared domain and service-layer contracts.

## Current status

The repository currently includes:

- Docker-based local development workflow
- PostgreSQL-backed Django app
- split development and test settings
- core accounts and returns domain models
- deterministic demo seed data
- public landing page and role entry routes
- authenticated console dashboards for admin, ops, customer, and merchant roles
- returns workflow API endpoints for create, detail, status, notes, and risk
- returns analytics API endpoint
- ML registry, feature contract, deterministic placeholder scoring, and persisted `RiskScore` output
- branded 403, 404, and 500 pages
- CI workflow for lint, format, tests, and coverage

## Product stance

ReturnHub is API-first for core workflow, with Django Templates, Bootstrap 5.3, and HTMX used for product surfaces built on the same domain model and service boundaries.

The UI is not treated as decoration. Public and authenticated surfaces exist to make workflow state, role boundaries, and operational context visible in the same product shell while the API and service layer remain the canonical source of behavior.

## Tech stack

- Python 3.12
- Django 5.x
- Django REST Framework
- PostgreSQL
- Docker Compose
- pytest and pytest-django
- factory_boy
- Ruff
- Black
- Bootstrap 5.3
- CSS design tokens

## Feature summary

### Reproducible environment

The application runs locally with Docker Compose and PostgreSQL. Split settings keep development and test concerns separate while keeping both environments aligned to PostgreSQL.

### Core domain models

The returns domain currently includes:

- `CustomerProfile`
- `MerchantProfile`
- `ReturnCase`
- `EvidenceDocument`
- `CaseNote`
- `CaseEvent`
- `RiskScore`

These models establish ownership boundaries, append-only audit structure, and persisted risk output for the implemented workflow.

### Deterministic demo data

A management command seeds stable demo users, groups, and return cases. The seed path is idempotent, so repeated runs do not inflate counts or create data drift. This makes API walkthroughs, UI checks, pagination verification, and permission tests reliable.

Demo users created by the seed command:

- `admin`
- `ops`
- `customer`
- `merchant`

Password for all local demo users:

- `password123`

### Public and authenticated UI surfaces

Public routes:

- `/`
- `/login/admin/`
- `/login/ops/`
- `/login/customer/`
- `/login/merchant/`

Authenticated console routes:

- `/console/admin/`
- `/console/ops/`
- `/console/customer/`
- `/console/merchant/`

The landing page is branded and responsive, with clear role entry points and a shared app shell. The authenticated console routes render role-aware dashboard shells inside the same visual system.

### Returns API and risk output

The returns workflow API currently includes:

- `POST /api/returns/`
- `GET /api/returns/{id}/`
- `PATCH /api/returns/{id}/status/`
- `POST /api/returns/{id}/notes/`
- `GET /api/returns/{id}/risk/`

Risk output is persisted to `RiskScore` records and exposed only to ops and admin users. Customer-facing case detail keeps `risk` hidden as `null`.

### Analytics and ML scaffolding

The project also includes:

- `GET /api/analytics/returns/` for bounded returns analytics
- a committed ML registry at `ml/registry/model_registry.json`
- deterministic placeholder scoring and reason-code generation
- persisted `risk_scored` audit events linked to return cases

### Shared pagination contract

ReturnHub adopts one pagination contract early so list pages do not drift. The shared utility and partial implement:

- `page` query parameter
- fixed page size of `15`
- missing page resolves to page 1
- invalid page resolves to page 1
- `page <= 0` resolves to page 1
- out-of-range page resolves to the last page
- filter-preserving page links
- count line format `Showing {start}-{end} of {total}`

## Repository structure

```text
.
├── accounts/
├── analytics/
│   ├── api/
│   └── services/
├── common/
│   ├── management/
│   └── templatetags/
├── config/
│   └── settings/
├── console/
├── docs/
│   ├── api/
│   ├── ml/
│   └── ui/
├── ml/
│   ├── contracts/
│   ├── datasets/
│   ├── management/
│   └── registry/
├── requirements/
├── returns/
│   ├── api/
│   ├── migrations/
│   └── services/
├── static/
│   ├── css/
│   └── images/
├── templates/
│   ├── console/
│   ├── errors/
│   ├── partials/
│   └── public/
├── tests/
├── ui/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── pyproject.toml
├── README.md
└── RUNBOOK.md
```

## Quick start

Clone the repository, create the environment file, start Docker services, run migrations, and seed demo data.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py seed_demo_data
```

Open the app at:

```text
http://127.0.0.1:8000/
```

Useful local surfaces:

- landing page: `/`
- public role entry pages: `/login/admin/`, `/login/ops/`, `/login/customer/`, `/login/merchant/`
- authenticated console pages: `/console/admin/`, `/console/ops/`, `/console/customer/`, `/console/merchant/`

## Local development commands

Run the test suite:

```bash
docker compose exec -T web pytest -q
```

Run lint checks:

```bash
docker compose exec -T web python -m ruff check .
```

Run formatting check:

```bash
docker compose exec -T web python -m black . --check
```

Create migrations after model changes:

```bash
docker compose exec -T web python manage.py makemigrations
```

Apply migrations:

```bash
docker compose exec -T web python manage.py migrate --noinput
```

Re-seed deterministic demo data:

```bash
docker compose exec -T web python manage.py seed_demo_data
```

Run tests with coverage:

```bash
docker compose exec -T web pytest -q --cov=. --cov-report=term-missing --cov-report=xml --cov-fail-under=80
```

## Local verification checklist

After setup, confirm the following:

- the landing page loads at `/`
- all four public surface entry pages load successfully
- authenticated console pages render for seeded users
- the seed command completes successfully
- `ReturnCase.objects.count()` returns `32`
- the returns API create and detail paths work
- the risk endpoint returns `200` for ops and `403` for customers and merchants
- pytest passes
- Ruff passes
- Black check passes
- custom 404 handling uses branded product templates

## Example expected outputs

Seed command:

```text
Seed complete. Stable return case count: 32
```

Pytest summary:

```text
<all tests pass>
```

Shell check for case count:

```text
32
```

Pagination count line example with seeded data:

```text
Showing 31-32 of 32
```

## Frontend artefacts

The repository includes reusable frontend building blocks such as:

- `docs/ui/product-ui-brief.md`
- `docs/ui/design-system.md`
- `templates/base.html`
- `templates/public/landing.html`
- `templates/public/surface_entry.html`
- `templates/console/admin_dashboard.html`
- `templates/console/ops_dashboard.html`
- `templates/console/customer_dashboard.html`
- `templates/console/merchant_dashboard.html`
- `templates/partials/_app_nav.html`
- `templates/partials/_flash_messages.html`
- `templates/partials/_empty_state.html`
- `templates/partials/_status_badge.html`
- `templates/partials/_pagination.html`
- `templates/errors/403.html`
- `templates/errors/404.html`
- `templates/errors/500.html`
- `static/css/tokens.css`
- `static/css/app.css`

## Quality bar

This project is being built with a production-minded quality bar:

- docstrings on public modules, classes, and functions
- shared contracts for behaviour that spans multiple surfaces
- database-backed integration tests for persistence-critical workflows
- deterministic demo data and predictable walkthroughs
- CI gates for lint, format, tests, and coverage
- accessible, responsive server-rendered UI foundations

## CI

GitHub Actions runs the following checks:

- migrations
- Ruff
- Black check
- pytest with coverage
- coverage threshold gate

## Troubleshooting

### Docker container does not start

Check container status:

```bash
docker compose ps
```

Inspect logs:

```bash
docker compose logs web
docker compose logs db
```

### PostgreSQL connection issue

Confirm `.env` exists and that these values are set correctly:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

### Tests fail because of stale local state

Reset containers and volumes, then rebuild:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py seed_demo_data
```

### `APIClient` requests fail in `manage.py shell`

When using `rest_framework.test.APIClient` in `manage.py shell`, pass `HTTP_HOST="localhost"` so the request uses an allowed host instead of the default `testserver`.

## Documentation

- `README.md` gives the project overview and setup path.
- `RUNBOOK.md` provides the current clone-to-verified workflow.
- `docs/api/returns-workflow.md` documents the returns workflow API.
- `docs/ml/model-registry.md` documents the ML registry contract.
- `docs/ui/product-ui-brief.md` defines the frontend purpose and layout direction.
- `docs/ui/design-system.md` defines the visual system foundation.

## License

MIT License.
