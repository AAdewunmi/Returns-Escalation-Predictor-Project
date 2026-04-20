<!-- path: docs/sprint-runbook/sprint-6/sprint-6-multi-surface-verification.md -->
# Multi-Surface Verification

This runbook verifies the current ReturnHub multi-surface experience using the live repository structure. It covers seeded demo access, public entry points, role-specific console routes, paginated surface routes, wrong-role handling, and the smoke tests that back those flows in the test suite.

For an executable version of this runbook, use:

```bash
./docs/sprint-runbook/sprint-6/sprint-6-multi-surface-verification.sh
```

The shell runbooks are written to fail with compact `CHECK_FAILED=` or `UNEXPECTED_ERROR=` lines instead of printing full Python tracebacks.

## Scope

This document is aligned to the current project state:

- Docker Compose is the primary local setup path
- deterministic demo data is provided by `seed_returnhub_demo`
- live seeded users are `admin.demo`, `ops.demo`, `customer.one`, `customer.two`, `merchant.one`, and `merchant.two`
- the smoke suite lives at `tests/test_surface_smoke.py`
- admin console verification is separate from admin cross-surface access verification

## Prerequisites

- Docker
- Docker Compose
- free local port `8000`
- a checked out copy of this repository

## Setup

Start from the repository root.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec -T web python manage.py migrate --noinput
docker compose exec -T web python manage.py seed_returnhub_demo
docker compose ps
```

Expected result:

- `web` is running
- the seed command reports `ReturnHub demo seed complete.`
- the seed command prints the seeded usernames
- the seed command prints `Seeded demo subset count: 32`
- the seed command may print a larger live `Total cases` value in non-pristine local databases

## Seeded Users

All seeded users use this password:

```text
ChangeMe123!
```

Seeded accounts:

- `admin.demo`
- `ops.demo`
- `customer.one`
- `customer.two`
- `merchant.one`
- `merchant.two`

## Public Surface Verification

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/login/admin/`
- `http://127.0.0.1:8000/login/ops/`
- `http://127.0.0.1:8000/login/customer/`
- `http://127.0.0.1:8000/login/merchant/`

Confirm the landing page shows:

- ReturnHub product framing
- the headline `Resolve return cases faster with one operational system of record.`
- an ops-focused primary call to action
- links or entry points for Admin, Ops, Customer, and Merchant login routes
- branded workflow/product copy rather than generic framework placeholder text

Confirm each `/login/<surface>/` page renders:

- a branded surface entry page
- the expected surface heading for that role
- shared shell styling consistent with the landing page

Reference coverage:

- `tests/test_public_views.py`

## Admin Surface Verification

Open `http://127.0.0.1:8000/login/admin/` and sign in as `admin.demo`.

Confirm:

- redirect to `/console/admin/`
- the admin console loads with HTTP `200`
- the page contains `Admin Console`
- the page exposes a link to `/admin/`
- the page reflects live case volume rather than a placeholder shell

This is the admin-owned smoke path reflected in `test_admin_can_open_admin_console`.

## Admin Cross-Surface Verification

While still signed in as `admin.demo`, open:

- `http://127.0.0.1:8000/customer/?page=1`
- `http://127.0.0.1:8000/customer/?page=2`

Confirm:

- both pages return HTTP `200`
- the admin account can inspect the customer surface without a wrong-role block

This is intentionally separate from the admin console smoke path and matches `test_admin_can_open_customer_portal_pages`.

## Ops Surface Verification

Open `http://127.0.0.1:8000/login/ops/` and sign in as `ops.demo`.

Confirm:

- redirect to `/console/ops/`
- `/console/ops/` returns HTTP `200`
- `/ops/?page=1` returns HTTP `200`
- `/ops/?page=2` returns HTTP `200`

Optional deeper manual check:

- verify the ops console shows queue-oriented language such as `Ops Console`

Reference coverage:

- `tests/test_surface_smoke.py`
- `tests/test_console_shell.py`

## Customer Surface Verification

Open `http://127.0.0.1:8000/login/customer/` and sign in as `customer.one`.

Confirm:

- redirect to `/console/customer/`
- `/console/customer/` returns HTTP `200`
- `/customer/?page=1` returns HTTP `200`
- `/customer/?page=2` returns HTTP `200`
- page 1 shows `Showing 1-15 of 16`
- page 2 shows `Showing 16-16 of 16`

Reference coverage:

- `tests/test_surface_smoke.py`
- `tests/test_customer_portal_views.py`

## Merchant Surface Verification

Open `http://127.0.0.1:8000/login/merchant/` and sign in as `merchant.one`.

Confirm:

- redirect to `/console/merchant/`
- `/console/merchant/` returns HTTP `200`
- `/merchant/?page=1` returns HTTP `200`
- `/merchant/?page=2` returns HTTP `200`
- page 1 shows `Showing 1-15 of 16`
- page 2 shows `Showing 16-16 of 16`

Reference coverage:

- `tests/test_surface_smoke.py`
- `tests/test_merchant_portal_views.py`

## Forbidden Handling Verification

Sign in as `customer.one`, then open:

- `http://127.0.0.1:8000/console/ops/`

Confirm:

- HTTP `403`
- the page contains `403 Forbidden`
- the page contains `This surface is outside your current access level.`
- the page contains `Go to sign in`
- the response is a branded forbidden page, not a raw Django permission error

Reference coverage:

- `tests/test_forbidden_template.py`

## Automated Validation

Run the focused verification suite:

```bash
docker compose exec web pytest -q \
  tests/test_public_views.py \
  tests/test_surface_smoke.py \
  tests/test_forbidden_template.py
```

Expected result:

- all referenced tests pass
- `tests/test_surface_smoke.py` reports `5 passed`

If you only want the seeded multi-surface smoke module:

```bash
docker compose exec web pytest -q tests/test_surface_smoke.py
```

Expected result:

- `5 passed`

## Related Files

- `tests/test_public_views.py`
- `tests/test_surface_smoke.py`
- `tests/test_forbidden_template.py`
- `tests/test_customer_portal_views.py`
- `tests/test_merchant_portal_views.py`
- `tests/test_console_shell.py`
- `returns/management/commands/seed_returnhub_demo.py`
- `templates/public/landing.html`
- `templates/console/admin_dashboard.html`
- `templates/errors/403.html`
