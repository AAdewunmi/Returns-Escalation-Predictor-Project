"""Coverage tests for core URL delegation."""

import importlib

from django.conf import settings as django_settings
from django.urls import resolve, reverse

import config.urls as project_urls
from core.urls import urlpatterns


def test_core_urls_delegate_to_live_route_modules() -> None:
    """Core URL mirrors should delegate to the live public and console routers."""
    assert len(urlpatterns) == 2
    assert urlpatterns[0].urlconf_name.__name__ == "ui.urls"
    assert urlpatterns[1].urlconf_name.__name__ == "console.urls"


def test_ops_namespace_routes_to_real_queue_page() -> None:
    """The /ops/ alias should resolve to the shared ops console view."""

    assert reverse("ops:queue") == "/ops/"
    assert resolve("/ops/").view_name == "ops:queue"


def test_ops_namespace_routes_to_real_case_detail_page() -> None:
    """The /ops/<id>/ alias should resolve to the shared ops case detail view."""

    assert reverse("ops:case-detail", kwargs={"case_id": 42}) == "/ops/42/"
    assert resolve("/ops/42/").view_name == "ops:case-detail"


def test_api_health_route_resolves_to_core_health_check() -> None:
    """The root router should expose the operational health endpoint."""

    assert reverse("core_api:health") == "/api/health/"
    assert resolve("/api/health/").view_name == "core_api:health"


def test_config_urls_appends_media_patterns_when_debug(monkeypatch) -> None:
    """Root URLs should append media-serving patterns in debug mode."""

    sentinel_pattern = object()

    with monkeypatch.context() as patch:
        static_calls = []

        def fake_static(prefix: str, *, document_root: str):
            static_calls.append((prefix, document_root))
            return [sentinel_pattern]

        patch.setattr("django.conf.urls.static.static", fake_static)
        patch.setattr(django_settings, "DEBUG", True)
        patch.setattr(django_settings, "MEDIA_URL", "/media/")
        patch.setattr(django_settings, "MEDIA_ROOT", "/tmp/returnhub-media")

        reloaded_urls = importlib.reload(project_urls)

        assert reloaded_urls.urlpatterns[-1] is sentinel_pattern
        assert static_calls == [("/media/", "/tmp/returnhub-media")]

    importlib.reload(project_urls)
