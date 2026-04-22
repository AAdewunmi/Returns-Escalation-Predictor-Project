# path: docker/entrypoint.sh
#!/usr/bin/env sh
set -eu

if [ "${DJANGO_SETTINGS_MODULE:-config.settings.dev}" = "config.settings.production" ]; then
    python manage.py check --deploy --fail-level "${DJANGO_DEPLOY_CHECK_FAIL_LEVEL:-WARNING}"
else
    python manage.py check
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
