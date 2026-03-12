# path: accounts/apps.py
"""Application configuration for account and profile models."""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Register the accounts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
