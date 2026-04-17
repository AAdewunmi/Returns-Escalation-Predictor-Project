# path: core/views/console.py
"""Compatibility shim for the live console views."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from accounts.mixins import is_admin_user, user_in_group
from console.views import (
    AdminConsoleView,
    CustomerConsoleView,
    MerchantConsoleView,
    OpsConsoleView,
)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Compatibility role guard retained for tests and older imports."""

    allowed_groups: tuple[str, ...] = ()
    raise_exception = True

    def test_func(self) -> bool:
        """Validate group membership for the current request."""
        user = self.request.user
        return is_admin_user(user) or any(
            user_in_group(user, group_name) for group_name in self.allowed_groups
        )


__all__ = [
    "AdminConsoleView",
    "CustomerConsoleView",
    "MerchantConsoleView",
    "OpsConsoleView",
    "RoleRequiredMixin",
]
