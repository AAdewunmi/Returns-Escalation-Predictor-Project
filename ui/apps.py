"""App configuration for user interface surfaces."""
from django.apps import AppConfig


class UiConfig(AppConfig):
    """Django config for the ui app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ui"
