# path: ui/urls.py
"""Public UI routes for ReturnHub."""
from django.urls import path

from ui.views import LandingView, SurfaceEntryView

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("login/admin/", SurfaceEntryView.as_view(), {"surface": "admin"}, name="admin-login"),
    path("login/ops/", SurfaceEntryView.as_view(), {"surface": "ops"}, name="ops-login"),
    path("login/customer/", SurfaceEntryView.as_view(), {"surface": "customer"}, name="customer-login"),
    path("login/merchant/", SurfaceEntryView.as_view(), {"surface": "merchant"}, name="merchant-login"),
]
