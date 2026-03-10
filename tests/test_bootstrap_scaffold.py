"""Coverage-focused tests for project bootstrap modules."""

import builtins
import importlib
import os
import sys

import pytest
from django.urls import resolve, reverse

import manage


def test_landing_route_renders_bootstrap_page(client):
    """Root route should render the scaffold landing template."""
    response = client.get(reverse("landing"))

    assert response.status_code == 200
    assert b"ReturnHub bootstrap is live." in response.content


def test_root_url_resolves_to_bootstrap_landing_view():
    """Project root should resolve to the expected view class."""
    match = resolve("/")

    assert match.view_name == "landing"
    assert match.func.view_class.__name__ == "BootstrapLandingView"


def test_manage_main_calls_execute_from_command_line(monkeypatch):
    """manage.main should delegate to Django's CLI entrypoint."""
    captured = {}

    def fake_execute(argv):
        captured["argv"] = argv

    monkeypatch.setattr("django.core.management.execute_from_command_line", fake_execute)
    monkeypatch.setattr(sys, "argv", ["manage.py", "check"])

    manage.main()

    assert captured["argv"] == ["manage.py", "check"]


def test_manage_main_raises_helpful_error_when_django_import_fails(monkeypatch):
    """manage.main should raise a clear ImportError message."""
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "django.core.management":
            raise ImportError("boom")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="Django could not be imported"):
        manage.main()


def test_dev_settings_debug_is_enabled():
    """Development settings should explicitly enable DEBUG."""
    settings_dev = importlib.import_module("config.settings.dev")

    assert settings_dev.DEBUG is True


def test_asgi_module_sets_default_settings_and_builds_application(monkeypatch):
    """ASGI module should set default settings module and create app object."""
    created = {}

    def fake_get_asgi_application():
        created["called"] = True
        return "asgi-app"

    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr("django.core.asgi.get_asgi_application", fake_get_asgi_application)
    sys.modules.pop("config.asgi", None)

    asgi_module = importlib.import_module("config.asgi")

    assert created["called"] is True
    assert asgi_module.application == "asgi-app"
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.dev"


def test_wsgi_module_sets_default_settings_and_builds_application(monkeypatch):
    """WSGI module should set default settings module and create app object."""
    created = {}

    def fake_get_wsgi_application():
        created["called"] = True
        return "wsgi-app"

    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr("django.core.wsgi.get_wsgi_application", fake_get_wsgi_application)
    sys.modules.pop("config.wsgi", None)

    wsgi_module = importlib.import_module("config.wsgi")

    assert created["called"] is True
    assert wsgi_module.application == "wsgi-app"
    assert os.environ["DJANGO_SETTINGS_MODULE"] == "config.settings.dev"
