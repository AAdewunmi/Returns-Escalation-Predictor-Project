"""Tests for account auth helpers, redirects, and surface login views."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse
from django.views import View

from accounts.mixins import (
    OpsSurfaceMixin,
    SurfaceAccessMixin,
    is_admin_user,
    user_has_surface_access,
    user_in_group,
)
from accounts.services.surface_redirects import (
    get_primary_surface,
    resolve_post_login_url,
    user_can_access_path,
)
from accounts.views_auth import OpsLoginView
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class DummySurfaceView(SurfaceAccessMixin, View):
    """Minimal view for exercising the shared surface access dispatch logic."""

    required_surface = "ops"

    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")


class MissingSurfaceView(SurfaceAccessMixin, View):
    """Minimal view with no required surface for misconfiguration tests."""

    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")


class DummyOpsSurfaceView(OpsSurfaceMixin, View):
    """Minimal ops view for subclass coverage."""

    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def test_user_in_group_returns_false_for_anonymous_user() -> None:
    """Anonymous users should never satisfy group checks."""

    assert user_in_group(AnonymousUser(), "Ops") is False


def test_is_admin_user_returns_true_for_superuser() -> None:
    """Superusers should be treated as admins for surface routing."""

    admin_user = UserFactory(is_superuser=True, is_staff=True)

    assert is_admin_user(admin_user) is True


def test_is_admin_user_returns_false_for_authenticated_non_admin() -> None:
    """Authenticated users without admin access should not count as admins."""

    user = UserFactory()

    assert is_admin_user(user) is False


def test_is_admin_user_returns_false_for_anonymous_user() -> None:
    """Anonymous users should never count as admins."""

    assert is_admin_user(AnonymousUser()) is False


def test_user_has_surface_access_for_matching_role() -> None:
    """Users should access only the surface that matches their role."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")

    assert user_has_surface_access(ops_user, "ops") is True
    assert user_has_surface_access(ops_user, "customer") is False


def test_user_has_surface_access_returns_false_for_unknown_role() -> None:
    """Unknown surface roles should be rejected."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")

    assert user_has_surface_access(ops_user, "unknown") is False


def test_user_has_surface_access_returns_true_for_superuser() -> None:
    """Superusers should be allowed onto every surface."""

    admin_user = UserFactory(is_superuser=True, is_staff=True)

    assert user_has_surface_access(admin_user, "ops") is True


def test_user_has_surface_access_returns_false_for_anonymous_user() -> None:
    """Anonymous users should never satisfy surface access checks."""

    assert user_has_surface_access(AnonymousUser(), "ops") is False


def test_get_primary_surface_prefers_first_matching_role() -> None:
    """Primary surface should follow the configured role priority."""

    multi_role_user = UserFactory()
    add_group(multi_role_user, "Customer")
    add_group(multi_role_user, "Merchant")

    assert get_primary_surface(multi_role_user) == "customer"


def test_get_primary_surface_falls_back_to_admin() -> None:
    """Users with no recognized groups should fall back to admin."""

    user = UserFactory()

    assert get_primary_surface(user) == "admin"


def test_user_can_access_path_allows_matching_surface_prefix() -> None:
    """Users may access next paths that belong to their own surface."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")

    assert user_can_access_path(ops_user, "/ops/") is True
    assert user_can_access_path(ops_user, "/console/ops/") is True
    assert user_can_access_path(ops_user, "/console/customer/") is False


def test_resolve_post_login_url_honours_safe_next_path_for_allowed_surface() -> None:
    """Safe next paths should win when the user may access them."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")

    assert resolve_post_login_url(ops_user, "ops", "/ops/") == "/ops/"


def test_resolve_post_login_url_rejects_disallowed_next_path() -> None:
    """Unsafe or unauthorized next paths should fall back to the console route."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")

    assert resolve_post_login_url(ops_user, "ops", "/console/customer/") == reverse(
        "accounts:console_ops"
    )


def test_resolve_post_login_url_falls_back_to_primary_surface_when_requested_surface_denied() -> (
    None
):
    """Users should be redirected to their primary allowed surface."""

    customer_user = UserFactory()
    add_group(customer_user, "Customer")

    assert resolve_post_login_url(customer_user, "ops") == reverse("accounts:console_customer")


def test_ops_login_view_get_success_url_uses_resolved_next_path() -> None:
    """Login views should delegate success URL resolution to the redirect service."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    request = RequestFactory().get("/login/ops/", {"next": "/ops/"})
    request.user = ops_user

    view = OpsLoginView()
    view.setup(request)

    assert view.get_success_url() == "/ops/"


def test_ops_login_view_context_exposes_surface_content() -> None:
    """Login views should expose surface metadata used by branded templates."""

    request = RequestFactory().get("/login/ops/")
    request.user = AnonymousUser()

    view = OpsLoginView()
    view.setup(request)
    view.object = None
    form = view.get_form()
    context = view.get_context_data(form=form)

    assert context["surface"] == "ops"
    assert context["surface_title"] == "Ops surface"
    assert context["surface_description"] == "Ops entry is reserved for queue-driven work."


def test_surface_access_mixin_redirects_anonymous_users_to_surface_login() -> None:
    """Anonymous requests should be redirected to the configured surface login."""

    request = RequestFactory().get("/console/ops/")
    request.user = AnonymousUser()

    response = DummySurfaceView.as_view()(request)

    assert response.status_code == 302
    assert response.url == f"{reverse('accounts:login_ops')}?next=/console/ops/"


def test_surface_access_mixin_raises_for_missing_required_surface() -> None:
    """Surface views must declare a required surface."""

    request = RequestFactory().get("/console/ops/")
    request.user = AnonymousUser()

    with pytest.raises(ValueError, match="required_surface must be set"):
        MissingSurfaceView.as_view()(request)


def test_surface_access_mixin_raises_permission_denied_for_wrong_role() -> None:
    """Authenticated users without surface access should receive a 403 contract."""

    customer_user = UserFactory()
    add_group(customer_user, "Customer")
    request = RequestFactory().get("/console/ops/")
    request.user = customer_user

    with pytest.raises(PermissionDenied, match="do not have access"):
        DummySurfaceView.as_view()(request)


def test_surface_access_mixin_allows_authorized_user_through_dispatch() -> None:
    """Authorized users should reach the wrapped view."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    request = RequestFactory().get("/console/ops/")
    request.user = ops_user

    response = DummySurfaceView.as_view()(request)

    assert response.status_code == 200
    assert response.content == b"ok"


def test_ops_surface_mixin_inherits_ops_surface_contract() -> None:
    """Concrete surface mixins should enforce the same access behavior."""

    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    request = RequestFactory().get("/console/ops/")
    request.user = ops_user

    response = DummyOpsSurfaceView.as_view()(request)

    assert response.status_code == 200
    assert response.content == b"ok"
