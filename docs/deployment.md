# Production Deployment

This repository defaults to `config.settings.dev` when `DJANGO_SETTINGS_MODULE`
is unset. Production deployment should override that explicitly in the
deployment platform, not through ad hoc shell exports.

## Required selection

Set this environment variable in the deployment platform:

```text
DJANGO_SETTINGS_MODULE=config.settings.production
```

This is the single explicit switch that enables the production settings module.

## Recommended production env template

Use [production.env.example](../production.env.example) as the deployment-facing
template for production configuration.

Key values:

- `DJANGO_SETTINGS_MODULE=config.settings.production`
- `DJANGO_SECRET_KEY=<strong secret>`
- `DJANGO_ALLOWED_HOSTS=<public hostnames>`
- `DJANGO_CSRF_TRUSTED_ORIGINS=<https origins>`
- `POSTGRES_*` database connection values
- `RELEASE_VERSION=<deployment identifier>`

## Verification

After deployment, verify that the process is using the production settings
module:

```bash
python manage.py shell -c "from django.conf import settings; print(settings.SETTINGS_MODULE)"
```

Expected output:

```text
config.settings.production
```

Verify the readiness endpoint exposes the deployed release identifier:

```bash
curl -s https://your-domain.example.com/api/health/ | python -m json.tool
```

Expected result:

- response contains `"status": "ok"` when the app is healthy
- response contains `"release": "<your deployed RELEASE_VERSION>"`

## Notes

- Keep `.env.example` for local development only.
- Do not rely on one-off `export DJANGO_SETTINGS_MODULE=...` commands during deploy.
- Keep production-only behavior in `config/settings/production.py`.
