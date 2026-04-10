# path: accounts/services/surface_redirects.py
"""Deterministic redirect helpers for ReturnHub surface login flows."""

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.constants import (
    PRIMARY_ROLE_ORDER,
    SURFACE_ALLOWED_PREFIXES,
    SURFACE_CONSOLE_ROUTE_NAMES,
)
from apps.accounts.mixins import is_admin_user, user_has_surface_access, user_in_group
from apps.accounts.constants import GROUP_NAMES


def get_primary_surface(user):
    """Return the user's primary surface in a stable priority order."""
    if is_admin_user(user):
        return "admin"

    for role in PRIMARY_ROLE_ORDER:
        if user_in_group(user, GROUP_NAMES[role]):
            return role

    return "admin"


def user_can_access_path(user, path):
    """Return True when the user may land on the requested relative path."""
    if is_admin_user(user):
        return True

    for role, prefixes in SURFACE_ALLOWED_PREFIXES.items():
        if path.startswith(prefixes):
            return user_has_surface_access(user, role)
    return False


def resolve_post_login_url(user, requested_surface, next_path=None):
    """Resolve the post-login destination for a surface entry point."""
    target_surface = requested_surface
    if not user_has_surface_access(user, requested_surface):
        target_surface = get_primary_surface(user)

    if next_path and url_has_allowed_host_and_scheme(
        url=next_path,
        allowed_hosts=set(),
        require_https=False,
    ):
        if next_path.startswith("/") and user_can_access_path(user, next_path):
            return next_path

    return reverse(SURFACE_CONSOLE_ROUTE_NAMES[target_surface])
