"""Console landing views for each ReturnHub surface."""

from console.views import (
    AdminConsoleView as BaseAdminConsoleView,
)
from console.views import (
    CustomerConsoleView as BaseCustomerConsoleView,
)
from console.views import (
    MerchantConsoleView as BaseMerchantConsoleView,
)
from console.views import (
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
