"""Application configuration for ML workflows."""

from django.apps import AppConfig


class MlConfig(AppConfig):
    """Register the ML app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ml"
