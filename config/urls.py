"""Top-level URL configuration for ReturnHub."""

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.api.views import HealthCheckView

handler403 = "ui.error_views.error_403"
handler404 = "ui.error_views.error_404"
handler500 = "ui.error_views.error_500"

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("ui.urls")),
    path(
        "customer/",
        include(("returns.urls_customer", "customer_portal"), namespace="customer_portal"),
    ),
    path(
        "merchant/",
        include(("returns.urls_merchant", "merchant_portal"), namespace="merchant_portal"),
    ),
    path("ops/", include(("returns.urls.ops", "ops"), namespace="ops")),
    path("console/", include("console.urls")),
    path("api/health/", HealthCheckView.as_view(), name="api-health"),
    path("api/analytics/", include("analytics.api.urls")),
    path("api/returns/", include("returns.api.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
