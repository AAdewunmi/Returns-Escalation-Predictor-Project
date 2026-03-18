# path: console/urls.py
"""URL routes for ReturnHub console shell pages."""

from __future__ import annotations

from django.urls import path

from console.views import (
    AdminConsoleView,
    CustomerConsoleView,
    MerchantConsoleView,
    OpsConsoleView,
)

app_name = "console"

urlpatterns = [
    path("admin/", AdminConsoleView.as_view(), name="admin-dashboard"),
    path("ops/", OpsConsoleView.as_view(), name="ops-dashboard"),
    path("customer/", CustomerConsoleView.as_view(), name="customer-dashboard"),
    path("merchant/", MerchantConsoleView.as_view(), name="merchant-dashboard"),
]
