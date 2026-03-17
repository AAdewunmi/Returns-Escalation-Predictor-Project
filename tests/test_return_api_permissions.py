"""Tests for returns API permission helpers."""

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory

from returns.api.permissions import IsCustomerOrAdmin, IsOpsOrAdmin, user_can_access_case
from tests.factories import ReturnCaseFactory, UserFactory


def _add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_user_can_access_case_for_supported_roles() -> None:
    """Access helper should allow the correct users for each role."""
    case = ReturnCaseFactory()
    customer_user = case.customer.user
    _add_group(customer_user, "Customer")

    merchant_user = case.merchant.user
    _add_group(merchant_user, "Merchant")

    ops_user = UserFactory()
    _add_group(ops_user, "Ops")

    admin_user = UserFactory(is_superuser=True)
    outsider = UserFactory()

    assert user_can_access_case(customer_user, case) is True
    assert user_can_access_case(merchant_user, case) is True
    assert user_can_access_case(ops_user, case) is True
    assert user_can_access_case(admin_user, case) is True
    assert user_can_access_case(outsider, case) is False
    assert user_can_access_case(AnonymousUser(), case) is False


@pytest.mark.django_db
def test_customer_or_admin_permission_allows_only_expected_roles() -> None:
    """Customer-or-admin permission should admit only those actors."""
    factory = RequestFactory()
    permission = IsCustomerOrAdmin()

    customer_user = UserFactory()
    _add_group(customer_user, "Customer")
    customer_request = factory.get("/api/returns/")
    customer_request.user = customer_user

    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    ops_request = factory.get("/api/returns/")
    ops_request.user = ops_user

    admin_user = UserFactory(is_superuser=True)
    admin_request = factory.get("/api/returns/")
    admin_request.user = admin_user

    anonymous_request = factory.get("/api/returns/")
    anonymous_request.user = AnonymousUser()

    assert permission.has_permission(customer_request, None) is True
    assert permission.has_permission(admin_request, None) is True
    assert permission.has_permission(ops_request, None) is False
    assert permission.has_permission(anonymous_request, None) is False


@pytest.mark.django_db
def test_ops_or_admin_permission_allows_only_expected_roles() -> None:
    """Ops-or-admin permission should admit only those actors."""
    factory = RequestFactory()
    permission = IsOpsOrAdmin()

    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    ops_request = factory.get("/api/returns/")
    ops_request.user = ops_user

    customer_user = UserFactory()
    _add_group(customer_user, "Customer")
    customer_request = factory.get("/api/returns/")
    customer_request.user = customer_user

    admin_user = UserFactory(is_superuser=True)
    admin_request = factory.get("/api/returns/")
    admin_request.user = admin_user

    anonymous_request = factory.get("/api/returns/")
    anonymous_request.user = AnonymousUser()

    assert permission.has_permission(ops_request, None) is True
    assert permission.has_permission(admin_request, None) is True
    assert permission.has_permission(customer_request, None) is False
    assert permission.has_permission(anonymous_request, None) is False
