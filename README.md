# ReturnHub

[![CI Pipeline](https://img.shields.io/github/actions/workflow/status/AAdewunmi/Returns-Escalation-Predictor-Project/ci.yml?branch=main)](https://github.com/AAdewunmi/Returns-Escalation-Predictor-Project/actions/workflows/ci.yml)
[![Code Style - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/)
[![Lint - Ruff](https://img.shields.io/badge/lint-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.x-0C4B33.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-336791.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-enabled-2496ED.svg)](https://www.docker.com/)
[![Docker Compose](https://img.shields.io/badge/docker%20compose-supported-2496ED.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/github/license/AAdewunmi/Returns-Escalation-Predictor-Project)](https://github.com/AAdewunmi/Returns-Escalation-Predictor-Project/blob/main/LICENSE)
[![Coverage Status](https://codecov.io/gh/AAdewunmi/Returns-Escalation-Predictor-Project/branch/main/graph/badge.svg)](https://codecov.io/gh/AAdewunmi/Returns-Escalation-Predictor-Project)

ReturnHub is a Django 5 application for managing online-retail return cases across customer, merchant, ops, and admin roles. The project combines server-rendered workflow surfaces with DRF APIs, a service-layer workflow core, persisted audit events, and artifact-backed escalation-risk scoring.

## Feature-complete state

Core ReturnHub development is complete as of April 23, 2026. The repository now represents a feature-complete portfolio baseline for the returns workflow product, including:

- Django 5.1 + Django REST Framework on Python 3.12
- PostgreSQL-backed local development through Docker Compose
- seeded demo users, groups, profiles, and 32 stable return cases
- public landing and role-entry pages
- authenticated console dashboards for admin, ops, customer, and merchant users
- customer and merchant case-list portals with stable pagination and role-bound access
- a standalone ops queue at `/ops/` with filtering, ordering, summary cards, and shared pagination
- an ops case-detail workspace at `/ops/{case_id}/` with inline status changes, follow-up requests, internal notes, timeline, risk panel, and evidence list
- a shared case detail route at `/cases/{case_id}/` with role-aware document visibility and inline uploads
- returns APIs for case creation, detail, status updates, notes, queue, documents, risk, and audit export
- bounded analytics at `/api/analytics/returns/`
- ML training, retraining, dataset generation, committed registry metadata, and persisted `RiskScore` records
- pytest coverage across the workflow, UI, ML, API, and operations layers

## Architecture

ReturnHub is organized around a shared domain model and service layer:

- `accounts/` defines customer and merchant profiles
- `returns/` owns return cases, documents, notes, audit events, risk persistence, workflow services, and ops APIs
- `api/` retains compatibility views and serializers that are not the default live route entry points
- `analytics/` exposes bounded return metrics for ops and admins
- `console/` serves authenticated dashboard and ops workflow pages
- `ui/` serves public pages, the shared case workspace, and branded error pages
- `ml/` owns feature extraction, scoring, model registry access, training flows, and reason-code generation
- `common/` provides shared pagination, context processors, and legacy demo-data seeding

## Architecture Note

The default live application entry points are:

- `config/urls.py` for route composition
- `console/` for authenticated console views
- `returns/` for workflow routes, services, and the live returns API
- `ui/` for public pages, shared case-detail pages, and branded error handling
- `analytics/api/` for bounded analytics endpoints

Compatibility and legacy layers retained in the repository:

- `api/` for compatibility API wiring and serializers that are not mounted as the default live router
- `core/` for compatibility mirrors used by older tests and imports
- `common.management.commands.seed_demo_data` for the older single-surface seed dataset
- `web/` as a reserved compatibility scaffold with no live route ownership

## Core domain

Main models:

- `CustomerProfile`
- `MerchantProfile`
- `ReturnCase`
- `EvidenceDocument`
- `CaseNote`
- `CaseEvent`
- `RiskScore`

`ReturnCase` supports these statuses:

- `submitted`
- `in_review`
- `waiting_customer`
- `waiting_merchant`
- `approved`
- `rejected`

`ReturnCase` supports these priorities:

- `low`
- `medium`
- `high`
- `urgent`

`EvidenceDocument` supports these kinds:

- `evidence`
- `response`

## Implemented surfaces

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

Workflow routes:

- `/customer/`
- `/customer/{case_id}/`
- `/merchant/`
- `/merchant/{case_id}/`
- `/ops/`
- `/ops/{case_id}/`
- `/cases/{case_id}/`
- `/cases/{case_id}/documents/upload/`

## API surface

Live application routes exposed by `config/urls.py`:

- `POST /api/returns/`
- `GET /api/returns/{case_id}/`
- `PATCH /api/returns/{case_id}/status/`
- `POST /api/returns/{case_id}/notes/`
- `GET /api/returns/queue/`
- `GET /api/returns/{case_id}/documents/`
- `POST /api/returns/{case_id}/documents/`
- `GET /api/returns/{case_id}/risk/`
- `GET /api/returns/{case_id}/audit-export/`
- `GET /api/analytics/returns/?from=YYYY-MM-DD&to=YYYY-MM-DD`

Behavioral rules enforced in code:

- customers and admins can create return cases
- ops and admins can update status, set priority, and add internal notes
- customers only see their own cases
- merchants only see cases tied to their merchant profile
- ops and admins can see all cases
- risk payloads are visible only to ops and admins
- customers can upload only `evidence` to their own cases
- merchants can upload only `response` to their own cases
- ops and admins can upload either document kind
- document uploads emit audit events and trigger a best-effort rescore

## Ops queue contract

The server-rendered ops queue and the DRF queue endpoint share the same service-layer contract:

- filters: `status`, `priority`, `risk_label`, `search`, `page`
- risk labels: `low`, `medium`, `high`
- page size: `15`
- invalid or missing page values normalize to page `1`
- ordering:
  1. SLA-breached active cases first
  2. higher priority first
  3. earlier `sla_due_at`
  4. earlier `created_at`
  5. `id` as final tiebreaker

## ML and analytics

The project includes:

- a committed feature contract at `ml/contracts/return_case_features.json`
- artifact-backed scoring with fallback placeholder scoring
- reason-code generation for persisted risk records
- a committed model registry at `ml/registry/model_registry.json`
- training, retraining, and dataset-generation management commands

The ML layer is production-path ready for this baseline: scoring is artifact-backed when the active model can be loaded, degrades safely to placeholder scoring when artifacts are unavailable, persists `RiskScore`, and emits `risk_scored` audit events.

Current committed active model:

- version: `retrain_baseline-logreg-v1-seed-7-rows-500`
- model type: `logistic_regression`
- contract version: `return-risk-sprint2-v1`
- reason code schema: `return-risk-reasons-sprint3-v1`

## Local setup

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py seed_returnhub_demo
```

Local health-check release identifier:

- set `RELEASE_VERSION` in `.env` to control the value returned by `/api/health/`
- examples: `RELEASE_VERSION=dev`, `RELEASE_VERSION=staging-2026-04-21`, `RELEASE_VERSION=prod-2026-04-21`
- set `DJANGO_SETTINGS_MODULE=config.settings.production` in `.env` to run the app with the production settings module instead of the default `config.settings.dev`
- use [production.env.example](production.env.example) and [docs/deployment.md](docs/deployment.md) for the production deployment path instead of reusing the local `.env.example`

Application URL:

```text
http://127.0.0.1:8000/
```

Demo users created by `seed_returnhub_demo`:

- `admin.demo`
- `ops.demo`
- `customer.one`
- `customer.two`
- `merchant.one`
- `merchant.two`

Shared local password:

- `ChangeMe123!`

Preferred seed command for manual verification and multi-surface demos:

- `docker compose exec -T web python manage.py seed_returnhub_demo`

Legacy compatibility seed still available for older workflows:

- `docker compose exec -T web python manage.py seed_demo_data`

## Useful commands

```bash
make bootstrap
make up
make migrate
make test
make test-cov
make lint
make format-check
make check
docker compose exec -T web python manage.py generate_training_dataset --seed 7 --rows 300
docker compose exec -T web python manage.py train_escalation_model --seed 7 --size 500
docker compose exec -T web python manage.py retrain_baseline_model --seed 7 --rows 500
```

## Repository map

```text
.
├── .dockerignore
├── .env.example
├── .github/
├── .gitattributes
├── .gitignore
├── accounts/
├── analytics/
├── api/
├── artifacts/
├── common/
├── config/
├── console/
├── core/
├── docker/
├── docs/
│   ├── api/
│   ├── ml/
│   ├── sprint-runbook/
│   └── ui/
├── infra/
├── ml/
├── ml_artifacts/
├── requirements/
├── returns/
├── static/
├── templates/
├── tests/
├── ui/
├── Dockerfile
├── Dockerfile.prod
├── LICENSE
├── Makefile
├── README.md
├── RUNBOOK.md
├── codecov.yml
├── docker-compose.prod.yml
├── docker-compose.yml
├── gunicorn.conf.py
├── manage.py
├── production.env.example
├── pyproject.toml
└── web/
```

## Documentation map

- `README.md`: project overview and feature-complete baseline summary
- `RUNBOOK.md`: bootstrap and manual verification flow
- `docs/api/returns-workflow.md`: returns API behavior and permissions
- `docs/api/ops-queue-contract.md`: shared queue filter, ordering, and pagination contract
- `docs/ml/baseline-escalation-risk.md`: training, inference, and artifact flow
- `docs/ml/model-registry.md`: registry structure and active-model metadata
- `docs/ml/operations.md`: ML operational readiness, scoring, and fallback behavior
- `docs/ui/product-ui-brief.md`: product-surface intent and route map
- `docs/ui/design-system.md`: tokens, layout patterns, and component rules
- `docs/ui/evidence-states.md`: case detail and document-upload state handling
- `docs/ui/visual-regression-checklist.md`: manual visual and responsive regression pass
- `docs/deployment.md`: production-like Docker, Gunicorn, Nginx, and PostgreSQL deployment path
- `docs/DEMO_SCRIPT.md`: deterministic feature-complete product walkthrough
- `docs/sprint-runbook/sprint-6/sprint-6-multi-surface-verification.md`: archived multi-surface verification flow retained for sprint evidence
