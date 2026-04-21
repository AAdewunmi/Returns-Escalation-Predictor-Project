"""Tests for production settings module behavior."""

from __future__ import annotations

import importlib
import sys

def test_production_settings_apply_env_driven_security_and_release_values(monkeypatch) -> None:
    """Production settings should expose the expected hardened env-driven values."""
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "app.example.com,api.example.com")
    monkeypatch.setenv(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://app.example.com,https://api.example.com",
    )
    monkeypatch.setenv("DJANGO_SECURE_SSL_REDIRECT", "false")
    monkeypatch.setenv("DJANGO_SESSION_COOKIE_SECURE", "0")
    monkeypatch.setenv("DJANGO_CSRF_COOKIE_SECURE", "1")
    monkeypatch.setenv("DJANGO_SECURE_HSTS_SECONDS", "86400")
    monkeypatch.setenv("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", "0")
    monkeypatch.setenv("DJANGO_SECURE_HSTS_PRELOAD", "false")
    monkeypatch.setenv("RELEASE_VERSION", "prod-2026-04-21")

    sys.modules.pop("config.settings.production", None)
    production_settings = importlib.import_module("config.settings.production")

    assert production_settings.DEBUG is False
    assert production_settings.ALLOWED_HOSTS == ["app.example.com", "api.example.com"]
    assert production_settings.CSRF_TRUSTED_ORIGINS == [
        "https://app.example.com",
        "https://api.example.com",
    ]
    assert production_settings.SECURE_SSL_REDIRECT is False
    assert production_settings.SESSION_COOKIE_SECURE is False
    assert production_settings.CSRF_COOKIE_SECURE is True
    assert production_settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert production_settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert production_settings.SECURE_HSTS_SECONDS == 86400
    assert production_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert production_settings.SECURE_HSTS_PRELOAD is False
    assert production_settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert production_settings.USE_X_FORWARDED_HOST is True
    assert production_settings.SECURE_REFERRER_POLICY == "same-origin"
    assert production_settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert production_settings.SECURE_CROSS_ORIGIN_OPENER_POLICY == "same-origin"
    assert production_settings.X_FRAME_OPTIONS == "DENY"
    assert production_settings.RELEASE_VERSION == "prod-2026-04-21"


def test_production_settings_fall_back_to_repo_defaults(monkeypatch) -> None:
    """Production settings should retain documented defaults when env vars are absent."""
    for name in [
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "DJANGO_SECURE_SSL_REDIRECT",
        "DJANGO_SESSION_COOKIE_SECURE",
        "DJANGO_CSRF_COOKIE_SECURE",
        "DJANGO_SECURE_HSTS_SECONDS",
        "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "DJANGO_SECURE_HSTS_PRELOAD",
        "RELEASE_VERSION",
    ]:
        monkeypatch.delenv(name, raising=False)

    sys.modules.pop("config.settings.production", None)
    production_settings = importlib.import_module("config.settings.production")

    assert production_settings.ALLOWED_HOSTS == ["localhost", "127.0.0.1"]
    assert production_settings.CSRF_TRUSTED_ORIGINS == ["https://localhost"]
    assert production_settings.SECURE_SSL_REDIRECT is True
    assert production_settings.SESSION_COOKIE_SECURE is True
    assert production_settings.CSRF_COOKIE_SECURE is True
    assert production_settings.SECURE_HSTS_SECONDS == 31536000
    assert production_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert production_settings.SECURE_HSTS_PRELOAD is True
    assert production_settings.RELEASE_VERSION == "dev"
