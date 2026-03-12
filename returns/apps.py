"""Application configuration for the returns app."""

from django.apps import AppConfig


class ReturnsConfig(AppConfig):
    """Register the returns app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "returns"
