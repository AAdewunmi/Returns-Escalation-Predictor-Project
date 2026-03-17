# path: returns/api/permissions.py
"""Permission helpers for the returns API."""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework.permissions import BasePermission

from returns.models import ReturnCase


def user_in_group(user: AbstractBaseUser, group_name: str) -> bool:
    """Return True when the user belongs to the supplied group or is superuser."""
    return user.is_superuser or user.groups.filter(name__iexact=group_name).exists()


def is_admin(user: AbstractBaseUser) -> bool:
    """Return True when the user is an admin."""
    return user_in_group(user, "admin")


def is_ops(user: AbstractBaseUser) -> bool:
    """Return True when the user is an ops user."""
    return user_in_group(user, "ops")


def is_customer(user: AbstractBaseUser) -> bool:
    """Return True when the user is a customer."""
    return user_in_group(user, "customer")


def is_merchant(user: AbstractBaseUser) -> bool:
    """Return True when the user is a merchant."""
    return user_in_group(user, "merchant")


def user_can_access_case(user: AbstractBaseUser, case: ReturnCase) -> bool:
    """Return True when the user is allowed to view the supplied case."""
    if not user.is_authenticated:
        return False

    if is_admin(user) or is_ops(user):
        return True

    if is_customer(user):
        return getattr(case.customer, "user_id", None) == user.id

    if is_merchant(user):
        return getattr(case.merchant, "user_id", None) == user.id

    return False


class IsCustomerOrAdmin(BasePermission):
    """Allow only customers and admins."""

    def has_permission(self, request, view) -> bool:
        """Evaluate the request-level permission."""
        return request.user.is_authenticated and (
            is_customer(request.user) or is_admin(request.user)
        )


class IsOpsOrAdmin(BasePermission):
    """Allow only ops and admins."""

    def has_permission(self, request, view) -> bool:
        """Evaluate the request-level permission."""
        return request.user.is_authenticated and (is_ops(request.user) or is_admin(request.user))
