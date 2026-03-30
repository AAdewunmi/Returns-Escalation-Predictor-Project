# path: core/urls.py
"""Core URL routes aligned with the live public and console shells."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("", include("ui.urls")),
    path("console/", include("console.urls")),
]
