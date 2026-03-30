"""Coverage tests for core URL delegation."""

from core.urls import urlpatterns


def test_core_urls_delegate_to_live_route_modules() -> None:
    """Core URL mirrors should delegate to the live public and console routers."""
    assert len(urlpatterns) == 2
    assert urlpatterns[0].urlconf_name.__name__ == "ui.urls"
    assert urlpatterns[1].urlconf_name.__name__ == "console.urls"
