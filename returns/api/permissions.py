"""Permission helpers for the returns API."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


def _user_in_group(user, group_name: str) -> bool:
    """Return True when the user belongs to the supplied Django group."""
    return user.is_superuser or user.groups.filter(name__iexact=group_name).exists()


def user_can_access_case(user, case) -> bool:
    """Return True when the user can access the supplied return case."""
    if not user.is_authenticated:
        return False
    if _user_in_group(user, "admin") or _user_in_group(user, "ops"):
        return True
    if _user_in_group(user, "customer"):
        return getattr(case.customer, "user_id", None) == user.id
    if _user_in_group(user, "merchant"):
        return getattr(case.merchant, "user_id", None) == user.id
    return False


class IsCustomerOrAdmin(BasePermission):
    """Allow access only to customer or admin users."""

    def has_permission(self, request, view) -> bool:
        """Return True when the current user is a customer or admin."""
        user = request.user
        return user.is_authenticated and (
            _user_in_group(user, "customer") or _user_in_group(user, "admin")
        )


class IsOpsOrAdmin(BasePermission):
    """Allow access only to ops or admin users."""

    def has_permission(self, request, view) -> bool:
        """Return True when the current user is ops or admin."""
        user = request.user
        return user.is_authenticated and (
            _user_in_group(user, "ops") or _user_in_group(user, "admin")
        )
