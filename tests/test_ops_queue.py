# path: returns/test_ops_queue.py
"""Integration tests for the ops queue surface."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories.accounts import UserFactory
from tests.factories.returns import CustomerProfileFactory, MerchantProfileFactory, ReturnCaseFactory


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_queue_requires_ops_role(client):
    """Authenticated non-ops users should receive a clean 403 page."""
    user = UserFactory()
    _add_group(user, "customer")
    client.force_login(user)

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 403
    assert "Forbidden" in response.content.decode()


@pytest.mark.django_db()
def test_ops_queue_uses_fixed_page_size_and_count_line(client):
    """The queue should paginate at 15 and expose the expected count line."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()

    for index in range(17):
        ReturnCaseFactory(
            reference=f"RC-{index:04d}",
            customer=customer,
            merchant=merchant,
            priority="normal",
            status="submitted",
        )

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 200
    assert response.context["page_obj"].number == 1
    assert len(response.context["page_obj"].object_list) == 15
    assert response.context["count_line"] == "Showing 1-15 of 17"


@pytest.mark.django_db()
def test_ops_queue_invalid_page_falls_back_to_first_page(client):
    """A non-integer page value should resolve to page one."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()

    for index in range(16):
        ReturnCaseFactory(
            reference=f"RC-A-{index:04d}",
            customer=customer,
            merchant=merchant,
        )

    response = client.get(reverse("ops:queue"), {"page": "abc"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 1


@pytest.mark.django_db()
def test_ops_queue_page_zero_falls_back_to_first_page(client):
    """A page number of zero should resolve to page one."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()

    for index in range(16):
        ReturnCaseFactory(
            reference=f"RC-Z-{index:04d}",
            customer=customer,
            merchant=merchant,
        )

    response = client.get(reverse("ops:queue"), {"page": "0"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 1


@pytest.mark.django_db()
def test_ops_queue_out_of_range_page_returns_last_page(client):
    """An out-of-range page should resolve to the final available page."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()

    for index in range(31):
        ReturnCaseFactory(
            reference=f"RC-L-{index:04d}",
            customer=customer,
            merchant=merchant,
        )

    response = client.get(reverse("ops:queue"), {"page": "999"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 3
    assert len(response.context["page_obj"].object_list) == 1


@pytest.mark.django_db()
def test_ops_queue_preserves_filters_in_query_string(client):
    """Pagination links should preserve active filters."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()

    for index in range(18):
        ReturnCaseFactory(
            reference=f"RC-F-{index:04d}",
            customer=customer,
            merchant=merchant,
            status="awaiting_customer",
            priority="high",
        )

    response = client.get(
        reverse("ops:queue"),
        {"status": "awaiting_customer", "priority": "high"},
    )

    assert response.status_code == 200
    assert response.context["query_string"] == "status=awaiting_customer&priority=high"
