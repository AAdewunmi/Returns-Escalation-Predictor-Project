"""Tests for surface access template tags."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Group

from accounts.templatetags.surface_access import (
    can_access_surface,
    has_group,
    is_admin_surface_user,
)
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def test_has_group_returns_true_for_matching_role_group() -> None:
    """The template filter should confirm membership for valid mapped roles."""

    merchant_user = UserFactory()
    add_group(merchant_user, "merchant")

    assert has_group(merchant_user, "merchant") is True


def test_has_group_returns_false_for_unknown_role() -> None:
    """The template filter should reject unknown role keys."""

    user = UserFactory()

    assert has_group(user, "unknown") is False


def test_can_access_surface_returns_true_for_allowed_surface() -> None:
    """The template filter should mirror the shared surface access helper."""

    customer_user = UserFactory()
    add_group(customer_user, "customer")

    assert can_access_surface(customer_user, "customer") is True


def test_can_access_surface_returns_false_for_unknown_surface() -> None:
    """Unknown surface names should be rejected by the template filter."""

    user = UserFactory()

    assert can_access_surface(user, "unknown") is False


def test_is_admin_surface_user_returns_true_for_superuser() -> None:
    """The simple tag should identify admin-capable users."""

    admin_user = UserFactory(is_superuser=True, is_staff=True)

    assert is_admin_surface_user(admin_user) is True


def test_is_admin_surface_user_returns_false_for_anonymous_user() -> None:
    """Anonymous users should never be treated as admin-capable."""

    assert is_admin_surface_user(AnonymousUser()) is False
