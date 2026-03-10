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

ReturnHub is a work-in-progress Django application for online retailer returns and customer support. It is designed as an API-first workflow product with server-rendered UI surfaces for ops teams, customers, merchants, and administrators. The system centralises return cases, evidence, notes, and audit events, with later sprints introducing case triage, multi-surface workflows, and escalation-risk scoring.

Sprint 1 establishes the reproducible foundation. The project now boots consistently with Docker and PostgreSQL, ships the first public product surface, defines the core domain models, seeds deterministic demo data, and introduces shared UI and pagination contracts that later sprints will inherit.

## Sprint 1 status

Sprint 1 is complete at foundation level. The repository now contains:

- Docker-based local development workflow
- PostgreSQL-backed Django app
- Split development and test settings
- Core accounts and returns domain models
- Deterministic demo seed command
- Shared pagination utility with fixed page size of 15
- Public landing page with branded role entry routes
- Shared design tokens and first-pass product shell
- Branded 403, 404, and 500 templates
- CI workflow for lint, format, tests, and coverage

## Product stance

ReturnHub is API-first for core workflow, with Django Templates, Bootstrap 5.3, and HTMX used for product surfaces built on the same domain model and service boundaries.

The public UI is not treated as decoration. The landing page and shared shell were shipped in Sprint 1 so the product feels intentional from the first click. Later sprints will add ops queue pages, customer and merchant portals, and role-aware login and console flows on top of the same domain rules.

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

## Sprint 1 feature summary

### Reproducible environment

The application runs locally with Docker Compose and PostgreSQL. Split settings keep development and test concerns separate while keeping both environments aligned to PostgreSQL.

### Core domain models

Sprint 1 introduces the first version of the domain model:

- `CustomerProfile`
- `MerchantProfile`
- `ReturnCase`
- `EvidenceDocument`
- `CaseNote`
- `CaseEvent`

These models establish ownership boundaries and append-only audit structure before API-first workflow logic arrives in Sprint 2.

### Deterministic demo data

A management command seeds stable demo users, groups, and return cases. The seed path is idempotent, so repeated runs do not inflate counts or create data drift. This makes later pagination checks, UI walkthroughs, and permission tests reliable.

Demo users created by the seed command:

- `admin`
- `ops`
- `customer`
- `merchant`

Password for all local demo users:

- `password123`

### Public UI foundation

Sprint 1 ships the first real product-facing public surface:

- `/`
- `/login/admin/`
- `/login/ops/`
- `/login/customer/`
- `/login/merchant/`

The landing page is branded and responsive, with clear role entry points and a shared app shell. These routes currently reserve the future login surfaces and keep the information architecture coherent before full auth routing lands.

### Shared pagination contract

ReturnHub adopts one pagination contract early so later list pages do not drift. The shared utility and partial implement:

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
├── common/
├── config/
├── docs/
│   └── ui/
├── requirements/
├── returns/
├── static/
│   └── css/
├── templates/
│   ├── errors/
│   ├── partials/
│   └── public/
├── tests/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── pyproject.toml
├── README.md
└── RUNBOOK.md
````

## Quick start

Clone the repository, create the environment file, start Docker services, run migrations, seed demo data, and start the app.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_data
docker compose exec web python manage.py runserver 0.0.0.0:8000
```

Open the app at:

```text
http://127.0.0.1:8000/
```

## Local development commands

Run the test suite:

```bash
docker compose exec web pytest -q
```

Run lint checks:

```bash
docker compose exec web ruff check .
```

Run formatting check:

```bash
docker compose exec web black --check .
```

Create migrations after model changes:

```bash
docker compose exec web python manage.py makemigrations
```

Apply migrations:

```bash
docker compose exec web python manage.py migrate
```

Re-seed deterministic demo data:

```bash
docker compose exec web python manage.py seed_demo_data
```

## Local verification checklist

After setup, confirm the following:

* the landing page loads at `/`
* all four surface entry pages load successfully
* the seed command completes successfully
* `ReturnCase.objects.count()` returns `32`
* pytest passes
* Ruff passes
* Black check passes
* the landing page shows four role entry cards
* custom 404 handling uses branded product templates

## Example expected outputs

Seed command:

```text
Seed complete. Stable return case count: 32
```

Pytest summary:

```text
14 passed in 1.10s
```

Shell check for case count:

```text
32
```

Pagination count line example with seeded data:

```text
Showing 31-32 of 32
```

## Frontend artefacts delivered in Sprint 1

Sprint 1 introduces the first reusable frontend building blocks:

* `docs/ui/product-ui-brief.md`
* `docs/ui/design-system.md`
* `templates/base.html`
* `templates/public/landing.html`
* `templates/public/surface_entry.html`
* `templates/partials/_app_nav.html`
* `templates/partials/_flash_messages.html`
* `templates/partials/_empty_state.html`
* `templates/partials/_status_badge.html`
* `templates/partials/_pagination.html`
* `templates/errors/403.html`
* `templates/errors/404.html`
* `templates/errors/500.html`
* `static/css/tokens.css`
* `static/css/app.css`

## Quality bar

This project is being built with a production-minded quality bar:

* docstrings on public modules, classes, and functions
* shared contracts for behaviour that will span multiple surfaces
* database-backed integration tests for persistence-critical workflows
* deterministic demo data and predictable walkthroughs
* CI gates for lint, format, tests, and coverage
* accessible, responsive server-rendered UI foundations

## CI

GitHub Actions runs the following checks:

* migrations
* Ruff
* Black check
* pytest with coverage
* coverage threshold gate

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

* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`
* `POSTGRES_HOST`
* `POSTGRES_PORT`

### Tests fail because of stale local state

Reset containers and volumes, then rebuild:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_data
```

## Sprint progression

Sprint 1 delivers the foundation only. Later sprints add API-first workflow logic, queue rules, evidence handling, ops actions, customer and merchant portals, ML scaffolding, scoring integration, and production deployment hardening.

## Documentation

* `README.md` gives the project overview and setup path.
* `RUNBOOK.md` provides the clean clone-to-verified workflow for Sprint 1.
* `docs/ui/product-ui-brief.md` defines the initial frontend purpose and layout direction.
* `docs/ui/design-system.md` defines the visual system foundation.

## License

MIT License.

