"""Coverage tests for core console view mirrors."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from django.test import RequestFactory

from core.views.console import (
    AdminConsoleView,
    CustomerConsoleView,
    MerchantConsoleView,
    OpsConsoleView,
    RoleRequiredMixin,
)
from returns.models import ReturnCase
from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


class RoleRequiredViewProbe(RoleRequiredMixin):
    """Minimal concrete view for exercising the role mixin."""

    allowed_groups = ("Ops",)


@pytest.mark.django_db
def test_role_required_mixin_allows_superusers() -> None:
    """Superusers should satisfy the role guard without group membership."""
    request = RequestFactory().get("/console/ops/")
    user = UserFactory(is_superuser=True, is_staff=True)
    view = RoleRequiredViewProbe()
    view.request = request
    request.user = user

    assert view.test_func() is True


@pytest.mark.django_db
def test_role_required_mixin_allows_matching_group_case_insensitively() -> None:
    """Role checks should be case-insensitive for configured group names."""
    request = RequestFactory().get("/console/ops/")
    user = UserFactory()
    add_group(user, "ops")
    view = RoleRequiredViewProbe()
    view.request = request
    request.user = user

    assert view.test_func() is True


@pytest.mark.django_db
def test_role_required_mixin_rejects_non_matching_users() -> None:
    """Users outside the allowed groups should fail the role check."""
    request = RequestFactory().get("/console/ops/")
    user = UserFactory()
    view = RoleRequiredViewProbe()
    view.request = request
    request.user = user

    assert view.test_func() is False


@pytest.mark.django_db
def test_admin_console_view_context_includes_page_title_and_total_cases() -> None:
    """Admin mirror view should expose the shared admin dashboard context."""
    request = RequestFactory().get("/console/admin/")
    request.user = AnonymousUser()
    ReturnCaseFactory.create_batch(3)

    view = AdminConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Admin Console"
    assert context["total_cases"] == 3


@pytest.mark.django_db
def test_ops_console_view_context_includes_queue_summary_and_pagination() -> None:
    """Ops mirror view should expose queue filters, counts, and pagination."""
    request = RequestFactory().get("/console/ops/", {"status": "submitted"})
    request.user = UserFactory()
    ReturnCaseFactory(
        status=ReturnCase.Status.SUBMITTED,
        order_reference="OPS-CORE-1",
    )
    ReturnCaseFactory(
        status=ReturnCase.Status.IN_REVIEW,
        order_reference="OPS-CORE-2",
    )

    view = OpsConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Ops Console"
    assert context["queue_filters"].status == "submitted"
    assert context["queue_summary"]["total"] == 1
    assert context["pagination"].count_line == "Showing 1-1 of 1"


@pytest.mark.django_db
def test_customer_console_view_context_includes_recent_cases_for_profile() -> None:
    """Customer mirror view should show only the current customer's cases."""
    customer_profile = CustomerProfileFactory()
    owned_case = ReturnCaseFactory(
        customer=customer_profile,
        order_reference="CORE-CUS-1",
    )
    ReturnCaseFactory(order_reference="CORE-CUS-2")
    request = RequestFactory().get("/console/customer/")
    request.user = customer_profile.user

    view = CustomerConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Customer Console"
    assert list(context["recent_cases"]) == [owned_case]


@pytest.mark.django_db
def test_customer_console_view_context_handles_missing_profile() -> None:
    """Customer mirror view should return an empty queryset without a profile."""
    request = RequestFactory().get("/console/customer/")
    request.user = UserFactory()

    view = CustomerConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Customer Console"
    assert list(context["recent_cases"]) == []


@pytest.mark.django_db
def test_merchant_console_view_context_includes_recent_cases_for_profile() -> None:
    """Merchant mirror view should show only the current merchant's cases."""
    merchant_profile = MerchantProfileFactory()
    owned_case = ReturnCaseFactory(
        merchant=merchant_profile,
        order_reference="CORE-MER-1",
    )
    ReturnCaseFactory(order_reference="CORE-MER-2")
    request = RequestFactory().get("/console/merchant/")
    request.user = merchant_profile.user

    view = MerchantConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Merchant Console"
    assert list(context["recent_cases"]) == [owned_case]


@pytest.mark.django_db
def test_merchant_console_view_context_handles_missing_profile() -> None:
    """Merchant mirror view should return an empty queryset without a profile."""
    request = RequestFactory().get("/console/merchant/")
    request.user = UserFactory()

    view = MerchantConsoleView()
    view.setup(request)
    context = view.get_context_data()

    assert context["page_title"] == "Merchant Console"
    assert list(context["recent_cases"]) == []
