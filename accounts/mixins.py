"""Shared account-role helpers for auth and surface routing."""

from __future__ import annotations

from accounts.constants import GROUP_NAMES, PRIMARY_ROLE_ORDER, ROLE_ADMIN


def user_in_group(user, group_name: str) -> bool:
    """Return True when the user belongs to the supplied group name."""

    if not getattr(user, "is_authenticated", False):
        return False

    return user.is_superuser or user.groups.filter(name__iexact=group_name).exists()


def is_admin_user(user) -> bool:
    """Return True when the user should be treated as an admin."""

    return user_in_group(user, GROUP_NAMES[ROLE_ADMIN])


def user_has_surface_access(user, role: str) -> bool:
    """Return True when the user may access the supplied product surface."""

    if not getattr(user, "is_authenticated", False):
        return False

    if is_admin_user(user):
        return True

    if role not in PRIMARY_ROLE_ORDER:
        return False

    return user_in_group(user, GROUP_NAMES[role])
