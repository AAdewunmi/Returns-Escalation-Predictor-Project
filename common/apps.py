"""App configuration for shared utilities."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    """Django config for the common app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "common"
