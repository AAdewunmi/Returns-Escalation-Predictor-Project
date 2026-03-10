# ReturnHub Sprint 1 Runbook

This runbook takes the project from clean clone to verified Sprint 1 state. It is written for deterministic local setup and manual verification. The goal is not only to start the application, but to prove that the Sprint 1 foundation is working as intended.

Sprint 1 verification covers environment setup, migrations, deterministic demo data, public UI routes, pagination contract checks, linting, formatting, tests, and expected visible behaviours.

## Scope

This runbook verifies the following Sprint 1 outcomes:

- Docker and PostgreSQL local environment
- Django project boot
- core migrations
- deterministic demo seed command
- public landing page and role entry pages
- branded error pages
- shared pagination utility contract
- test suite, lint, format, and coverage checks

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
````

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
docker compose exec web python manage.py migrate
```

Expected result:

```text
Django applies built-in migrations plus the Sprint 1 `accounts` and `returns` migrations without errors.
```

## Seed deterministic demo data

Run the seed command.

```bash
docker compose exec web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

Run the seed command a second time to confirm idempotency.

```bash
docker compose exec web python manage.py seed_demo_data
```

Expected result:

```text
Seed complete. Stable return case count: 32
```

## Verify demo users and seeded case count

Check the total return case count.

```bash
docker compose exec web python manage.py shell -c "from returns.models import ReturnCase; print(ReturnCase.objects.count())"
```

Expected result:

```text
32
```

Check that the expected role groups exist.

```bash
docker compose exec web python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.order_by('name').values_list('name', flat=True)))"
```

Expected result:

```text
['Admin', 'Customer', 'Merchant', 'Ops']
```

Check the expected local demo usernames.

```bash
docker compose exec web python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(list(User.objects.order_by('username').values_list('username', flat=True)))"
```

Expected result:

```text
['admin', 'customer', 'merchant', 'ops']
```

## Start the application server

Start the Django development server inside the container.

```bash
docker compose exec web python manage.py runserver 0.0.0.0:8000
```

Expected result:

```text
The server starts without import, migration, or template errors.
```

## Public route verification

Open the landing page in a browser.

```text
http://127.0.0.1:8000/
```

Expected visible behaviour:

* the page title shows ReturnHub branding
* the landing page headline explains the returns workflow product
* four role entry cards are visible
* buttons exist for Admin, Ops, Customer, and Merchant
* the layout feels branded and not like a default Django page

Open the admin surface entry page.

```text
http://127.0.0.1:8000/login/admin/
```

Expected visible behaviour:

* a branded page loads successfully
* the page explains that the admin entry is reserved and branded
* the page provides a route back to the landing page

Open the ops surface entry page.

```text
http://127.0.0.1:8000/login/ops/
```

Expected visible behaviour:

* a branded page loads successfully
* the page explains that the ops entry is reserved for queue-driven work

Open the customer surface entry page.

```text
http://127.0.0.1:8000/login/customer/
```

Expected visible behaviour:

* a branded page loads successfully
* the page explains that the customer entry is reserved for case tracking

Open the merchant surface entry page.

```text
http://127.0.0.1:8000/login/merchant/
```

Expected visible behaviour:

* a branded page loads successfully
* the page explains that the merchant entry is reserved for linked case responses

## Responsive UI check

Use browser dev tools to test the landing page at smaller widths.

```text
Mobile width example: 390px
Tablet width example: 768px
Desktop width example: 1280px
```

Expected visible behaviour:

* role cards stack cleanly at narrow widths
* navigation remains readable
* primary action buttons remain visible without awkward overlap
* spacing and hierarchy stay coherent

## Pagination contract verification

Check the fallback for out-of-range page numbers using the shared pagination utility.

```bash
docker compose exec web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), '999').count_line)"
```

Expected result:

```text
Showing 31-32 of 32
```

Check invalid-page fallback.

```bash
docker compose exec web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), 'banana').page_obj.number)"
```

Expected result:

```text
1
```

Check zero-page fallback.

```bash
docker compose exec web python manage.py shell -c "from returns.models import ReturnCase; from common.pagination import paginate_queryset; print(paginate_queryset(ReturnCase.objects.order_by('id'), '0').page_obj.number)"
```

Expected result:

```text
1
```

## Test verification

Run the test suite.

```bash
docker compose exec web pytest -q
```

Expected result:

```text
14 passed in 1.10s
```

Run tests with coverage.

```bash
docker compose exec web pytest --cov=. --cov-report=term-missing --cov-fail-under=85 -q
```

Expected result:

```text
The test suite passes and the total coverage meets or exceeds 85%.
```

## Lint and format verification

Run Ruff.

```bash
docker compose exec web ruff check .
```

Expected result:

```text
All checks passed!
```

Run Black format check.

```bash
docker compose exec web black --check .
```

Expected result:

```text
All done! No files would be reformatted.
```

## Error page verification

A branded 404 page should render for unknown routes when `DEBUG=False`. This is already covered by tests, but it can also be checked manually in a non-development configuration if needed.

Open an unknown route.

```text
http://127.0.0.1:8000/not-a-real-page/
```

Expected visible behaviour in non-debug mode:

* a branded 404 page renders
* the page uses the shared app shell
* the page provides a clear recovery path back to the landing page

## Sprint 1 definition of done checklist

Sprint 1 should be considered verified when all items below are true:

* containers build and start successfully
* migrations apply successfully
* demo data seeds successfully
* repeated seeding keeps the case count at `32`
* landing page loads successfully
* all four role entry routes load successfully
* pagination fallback checks return expected results
* pytest passes
* coverage gate passes
* Ruff passes
* Black check passes

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
docker compose exec web python manage.py migrate
```

Expected result:

```text
The database schema is recreated cleanly.
```

Re-seed demo data.

```bash
docker compose exec web python manage.py seed_demo_data
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

### Tests fail after local experimentation

Use the clean reset procedure, then rerun migrations, seed data, and tests.

## End state

At the end of this runbook, the local environment should be in a verified Sprint 1 state with a working public landing page, deterministic demo dataset, shared pagination contract, passing tests, and CI-equivalent local quality checks.