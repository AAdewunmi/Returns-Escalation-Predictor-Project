# path: accounts/urls.py
"""URL routes for surface-specific authentication and console pages."""

from django.contrib.auth.views import LogoutView
from django.urls import path

from .views_auth import AdminLoginView, CustomerLoginView, MerchantLoginView, OpsLoginView
from .views_console import (
    AdminConsoleView,
    CustomerConsoleView,
    MerchantConsoleView,
    OpsConsoleView,
)

app_name = "accounts"

urlpatterns = [
    path("login/admin/", AdminLoginView.as_view(), name="login_admin"),
    path("login/ops/", OpsLoginView.as_view(), name="login_ops"),
    path("login/customer/", CustomerLoginView.as_view(), name="login_customer"),
    path("login/merchant/", MerchantLoginView.as_view(), name="login_merchant"),
    path("console/admin/", AdminConsoleView.as_view(), name="console_admin"),
    path("console/ops/", OpsConsoleView.as_view(), name="console_ops"),
    path("console/customer/", CustomerConsoleView.as_view(), name="console_customer"),
    path("console/merchant/", MerchantConsoleView.as_view(), name="console_merchant"),
    path("logout/", LogoutView.as_view(next_page="landing"), name="logout"),
]