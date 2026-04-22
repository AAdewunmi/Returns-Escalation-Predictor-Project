# ReturnHub Deployment

## Purpose

This document defines the production-like deployment path for ReturnHub using
Docker, Gunicorn, Nginx, and PostgreSQL. The goal is not to support every
hosting platform abstraction. The goal is to make one clear operator path that
can be followed locally, in staging, or in a VM-based deployment with minimal
translation.

This repository defaults to `config.settings.dev` when
`DJANGO_SETTINGS_MODULE` is unset. Production deployment should override that
explicitly in the deployment platform, not through ad hoc shell exports.

## Required selection

Set this environment variable in the deployment platform:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
```

This is the single explicit switch that enables the production settings module.

## Required environment variables

Use [production.env.example](../production.env.example) as the deployment-facing
template and create a real `production.env` file for the Compose-based
production stack.

The current production settings in this repo read `POSTGRES_*` values directly.
They do not currently read `DATABASE_URL`, so `DATABASE_URL` is not part of the
required env contract here.

For the repo's canonical Compose-based production-like stack, `POSTGRES_HOST`
should be `db` so the web container connects to the Compose database service.

Minimum aligned example:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=replace-with-a-strong-secret
DJANGO_ALLOWED_HOSTS=your-domain.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.example.com
POSTGRES_DB=returnhub
POSTGRES_USER=returnhub
POSTGRES_PASSWORD=replace-with-a-production-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
RELEASE_VERSION=2026.03.09
```

Local or staging production-like verification may also override security flags
when HTTPS termination is not in place yet. For example:

```bash
DJANGO_SECURE_SSL_REDIRECT=0
DJANGO_SESSION_COOKIE_SECURE=0
DJANGO_CSRF_COOKIE_SECURE=0
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_DEPLOY_CHECK_FAIL_LEVEL=ERROR
```

The production Compose stack builds `Dockerfile.prod`, which installs
`requirements/prod.txt` instead of the dev dependency set.

## Canonical compose path

```bash
cp production.env.example production.env
docker compose -f docker-compose.prod.yml up --build -d
```

The canonical production-like stack is:

- `db`
- `web`
- `nginx`

## Operator sequence

Use this exact sequence to move from image build to a healthy application:

1. Create and review `production.env` from `production.env.example`.
2. Start the stack:

   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```

3. Confirm the services are running:

   ```bash
   docker compose -f docker-compose.prod.yml ps
   ```

4. Verify the app process is using `config.settings.production`.
5. Verify `/api/health/` returns a healthy readiness payload.
6. Verify the landing page responds through Nginx with the expected security headers.

The application should be considered healthy only after the entrypoint has
completed Django checks, migrations, and `collectstatic`, and after Gunicorn and
Nginx are both serving requests successfully.

## Verification

After deployment, verify that the process is using the production settings
module:

```bash
docker compose -f docker-compose.prod.yml exec web \
  python manage.py shell -c "from django.conf import settings; print(settings.SETTINGS_MODULE)"
```

Expected output:

```text
config.settings.production
```

Verify the readiness endpoint exposes the deployed release identifier:

```bash
curl -s http://127.0.0.1/api/health/ | python -m json.tool
```

Expected result:

- response contains `"status": "ok"` when the app is healthy
- response contains `"release": "<your deployed RELEASE_VERSION>"`

Verify the landing page headers through the reverse proxy:

```bash
curl -I http://127.0.0.1/
```

Expected result includes:

- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `X-Content-Type-Options: nosniff`

## Notes

- Keep `.env.example` for local development only.
- Keep `production.env.example` as the template for the production-like stack.
- Do not rely on one-off `export DJANGO_SETTINGS_MODULE=...` commands during deploy.
- Keep production-only behavior in `config/settings/production.py`.
- Keep `Dockerfile.prod` and `requirements/prod.txt` as the production image path.
