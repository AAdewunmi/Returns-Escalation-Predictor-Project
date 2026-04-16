# path: accounts/templatetags/surface_access.py
"""Template tags for surface-aware navigation and access checks."""

from django import template

from apps.accounts.constants import GROUP_NAMES, ROLE_ADMIN, ROLE_CUSTOMER, ROLE_MERCHANT, ROLE_OPS
from apps.accounts.mixins import is_admin_user, user_in_group, user_has_surface_access

register = template.Library()


@register.filter
def has_group(user, role):
    """Return True when the user belongs to the requested role group."""
    if role not in GROUP_NAMES:
        return False
    return user_in_group(user, GROUP_NAMES[role])


@register.filter
def can_access_surface(user, role):
    """Return True when the user may access the requested surface."""
    if role not in {ROLE_ADMIN, ROLE_OPS, ROLE_CUSTOMER, ROLE_MERCHANT}:
        return False
    return user_has_surface_access(user, role)


@register.simple_tag
def is_admin_surface_user(user):
    """Return True when the current user is an admin."""
    return is_admin_user(user)
