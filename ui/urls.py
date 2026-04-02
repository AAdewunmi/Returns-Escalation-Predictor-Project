# path: ui/urls.py
"""Public UI routes for ReturnHub."""
from django.urls import path

from ui.views import BootstrapLandingView, ReturnCaseDetailView, SurfaceEntryView

urlpatterns = [
    path("", BootstrapLandingView.as_view(), name="landing"),
    path("cases/<int:case_id>/", ReturnCaseDetailView.as_view(), name="case-detail"),
    path("login/admin/", SurfaceEntryView.as_view(), {"surface": "admin"}, name="admin-login"),
    path("login/ops/", SurfaceEntryView.as_view(), {"surface": "ops"}, name="ops-login"),
    path(
        "login/customer/",
        SurfaceEntryView.as_view(),
        {"surface": "customer"},
        name="customer-login",
    ),
    path(
        "login/merchant/",
        SurfaceEntryView.as_view(),
        {"surface": "merchant"},
        name="merchant-login",
    ),
]
