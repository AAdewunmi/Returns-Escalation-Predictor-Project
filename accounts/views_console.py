"""Console landing views for each ReturnHub surface."""

from console.views import (
    AdminConsoleView as BaseAdminConsoleView,
    CustomerConsoleView as BaseCustomerConsoleView,
    MerchantConsoleView as BaseMerchantConsoleView,
    OpsConsoleView as BaseOpsConsoleView,
)


class AdminConsoleView(BaseAdminConsoleView):
    """Admin console entry page."""


class OpsConsoleView(BaseOpsConsoleView):
    """Ops console entry page."""


class CustomerConsoleView(BaseCustomerConsoleView):
    """Customer console entry page."""


class MerchantConsoleView(BaseMerchantConsoleView):
    """Merchant console entry page."""


__all__ = [
    "AdminConsoleView",
    "OpsConsoleView",
    "CustomerConsoleView",
    "MerchantConsoleView",
]
