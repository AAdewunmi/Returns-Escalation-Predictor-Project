"""Health and readiness checks used by deployment and monitoring tooling."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone


def check_database() -> tuple[bool, str]:
    """Return whether the default database is reachable.

    The readiness check uses a lightweight ``SELECT 1`` probe so the endpoint
    verifies the actual connection path that the application depends on in
    production. The text message is intentionally stable because external
    tooling may display or log it directly.
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return False, "unavailable"

    return True, "ok"


def get_readiness_payload() -> dict[str, Any]:
    """Build the stable readiness payload returned by ``/api/health/``.

    Returns:
        A serialisable dictionary containing the service status, a release
        identifier, a UTC timestamp, and named dependency checks.
    """
    database_ok, database_status = check_database()
    overall_status = "ok" if database_ok else "degraded"

    return {
        "status": overall_status,
        "service": "returnhub",
        "release": getattr(settings, "RELEASE_VERSION", "dev"),
        "timestamp": timezone.now().isoformat(),
        "checks": {
            "database": database_status,
        },
    }
