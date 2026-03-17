# path: config/urls.py
"""URL configuration for ReturnHub."""
from django.contrib import admin
from django.urls import include, path

handler403 = "ui.error_views.error_403"
handler404 = "ui.error_views.error_404"
handler500 = "ui.error_views.error_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ui.urls")),
    path("api/returns/", include("returns.api.urls")),
]
