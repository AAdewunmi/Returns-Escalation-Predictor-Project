"""Compatibility console views exposed through the accounts app."""

from console.views import (
    AdminConsoleView,
    CustomerConsoleView,
    MerchantConsoleView,
    OpsConsoleView,
)

__all__ = [
    "AdminConsoleView",
    "OpsConsoleView",
    "CustomerConsoleView",
    "MerchantConsoleView",
]
