"""Tests for shared template context processors."""

from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory

from common.context_processors import app_shell
from tests.factories import UserFactory


def test_app_shell_returns_public_defaults_for_anonymous_requests() -> None:
    """Anonymous requests should expose the public shell defaults."""
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    context = app_shell(request)

    assert context == {
        "brand_name": "ReturnHub",
        "active_role_groups": [],
        "current_path": "/",
    }


def test_app_shell_returns_sorted_role_groups_for_authenticated_users(db) -> None:
    """Authenticated requests should expose ordered role group names."""
    request = RequestFactory().get("/ops/")
    user = UserFactory()
    ops_group = Group.objects.create(name="Ops")
    admin_group = Group.objects.create(name="Admin")
    user.groups.set([ops_group, admin_group])
    request.user = user

    context = app_shell(request)

    assert context == {
        "brand_name": "ReturnHub",
        "active_role_groups": ["Admin", "Ops"],
        "current_path": "/ops/",
    }
