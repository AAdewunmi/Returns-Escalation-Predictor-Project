"""Surface-aware access control mixins for ReturnHub."""

from __future__ import annotations

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

from accounts.constants import (
    GROUP_NAMES,
    ROLE_ADMIN,
    ROLE_CUSTOMER,
    ROLE_MERCHANT,
    ROLE_OPS,
    SURFACE_LOGIN_ROUTE_NAMES,
)


def user_in_group(user, group_name: str) -> bool:
    """Return True when the user belongs to the given Django group."""

    if not getattr(user, "is_authenticated", False):
        return False

    return user.groups.filter(name__iexact=group_name).exists()


def is_admin_user(user) -> bool:
    """Return True when the user has administrative access."""

    if not getattr(user, "is_authenticated", False):
        return False

    return user.is_superuser or user_in_group(user, GROUP_NAMES[ROLE_ADMIN])


def user_has_surface_access(user, role: str) -> bool:
    """Return True when the user may access the requested product surface."""

    if not getattr(user, "is_authenticated", False):
        return False

    surface_group_lookup = {
        ROLE_OPS: GROUP_NAMES[ROLE_OPS],
        ROLE_CUSTOMER: GROUP_NAMES[ROLE_CUSTOMER],
        ROLE_MERCHANT: GROUP_NAMES[ROLE_MERCHANT],
        ROLE_ADMIN: GROUP_NAMES[ROLE_ADMIN],
    }
    if role not in surface_group_lookup:
        return False

    if role == ROLE_ADMIN:
        return is_admin_user(user)

    return user_in_group(user, surface_group_lookup[role])


class SurfaceAccessMixin:
    """Redirect anonymous users to the correct surface login and 403 wrong-role users."""

    required_surface: str | None = None

    def dispatch(self, request, *args, **kwargs):
        """Apply the surface login redirect or 403 contract before handling the request."""

        if self.required_surface is None:
            raise ValueError("required_surface must be set on SurfaceAccessMixin subclasses.")

        if not request.user.is_authenticated:
            login_url = resolve_url(SURFACE_LOGIN_ROUTE_NAMES[self.required_surface])
            return redirect_to_login(request.get_full_path(), login_url)

        if not user_has_surface_access(request.user, self.required_surface):
            raise PermissionDenied("You do not have access to this ReturnHub surface.")

        return super().dispatch(request, *args, **kwargs)


class AdminSurfaceMixin(SurfaceAccessMixin):
    """Restrict a view to the admin surface."""

    required_surface = ROLE_ADMIN


class OpsSurfaceMixin(SurfaceAccessMixin):
    """Restrict a view to the ops surface or admin override."""

    required_surface = ROLE_OPS


class CustomerSurfaceMixin(SurfaceAccessMixin):
    """Restrict a view to the customer surface or admin override."""

    required_surface = ROLE_CUSTOMER


class MerchantSurfaceMixin(SurfaceAccessMixin):
    """Restrict a view to the merchant surface or admin override."""

    required_surface = ROLE_MERCHANT
