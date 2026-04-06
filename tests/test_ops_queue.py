"""Integration tests for the standalone ops queue route."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories import ReturnCaseFactory, RiskScoreFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def ops_user() -> UserFactory:
    """Create a user with ops access."""

    user = UserFactory()
    add_group(user, "Ops")
    return user


@pytest.mark.django_db
def test_ops_queue_requires_ops_role(client) -> None:
    """Authenticated non-ops users should receive a clean 403 page."""

    user = UserFactory()
    add_group(user, "Customer")
    client.force_login(user)

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 403
    assert "Forbidden" in response.content.decode()


@pytest.mark.django_db
def test_ops_queue_uses_fixed_page_size_and_pagination_context(client) -> None:
    """The /ops/ queue should paginate at 15 and expose the shared count line."""

    client.force_login(ops_user())

    for index in range(17):
        ReturnCaseFactory(
            order_reference=f"OPS-{index:04d}",
            priority="medium",
            status="submitted",
        )

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 200
    assert response.context["pagination"].page_obj.number == 1
    assert len(response.context["pagination"].page_obj.object_list) == 15
    assert response.context["pagination"].count_line == "Showing 1-15 of 17"


@pytest.mark.django_db
def test_ops_queue_invalid_page_falls_back_to_first_page(client) -> None:
    """A non-integer page value should resolve to page one."""

    client.force_login(ops_user())

    for index in range(16):
        ReturnCaseFactory(order_reference=f"OPS-A-{index:04d}")

    response = client.get(reverse("ops:queue"), {"page": "abc"})

    assert response.status_code == 200
    assert response.context["pagination"].page_obj.number == 1


@pytest.mark.django_db
def test_ops_queue_page_zero_falls_back_to_first_page(client) -> None:
    """A page number of zero should resolve to page one."""

    client.force_login(ops_user())

    for index in range(16):
        ReturnCaseFactory(order_reference=f"OPS-Z-{index:04d}")

    response = client.get(reverse("ops:queue"), {"page": "0"})

    assert response.status_code == 200
    assert response.context["pagination"].page_obj.number == 1


@pytest.mark.django_db
def test_ops_queue_out_of_range_page_returns_last_page(client) -> None:
    """An out-of-range page should resolve to the final available page."""

    client.force_login(ops_user())

    for index in range(31):
        ReturnCaseFactory(order_reference=f"OPS-L-{index:04d}")

    response = client.get(reverse("ops:queue"), {"page": "999"})

    assert response.status_code == 200
    assert response.context["pagination"].page_obj.number == 3
    assert len(response.context["pagination"].page_obj.object_list) == 1


@pytest.mark.django_db
def test_ops_queue_exposes_queue_filters_and_preserves_query_params(client) -> None:
    """The standalone queue should expose active filters and preserve them in pagination."""

    client.force_login(ops_user())

    for index in range(18):
        case = ReturnCaseFactory(
            order_reference=f"OPS-F-{index:04d}",
            status="waiting_customer",
            priority="high",
        )
        RiskScoreFactory(case=case, label="high")

    ReturnCaseFactory(order_reference="OPS-OTHER-1", status="submitted", priority="low")

    response = client.get(
        reverse("ops:queue"),
        {
            "status": "waiting_customer",
            "priority": "high",
            "risk_label": "high",
            "page": 2,
        },
    )

    body = response.content.decode()

    assert response.status_code == 200
    assert response.context["queue_filters"].status == "waiting_customer"
    assert response.context["queue_filters"].priority == "high"
    assert response.context["queue_filters"].risk_label == "high"
    assert response.context["pagination"].page_obj.number == 2
    assert "status=waiting_customer" in body
    assert "priority=high" in body
    assert "risk_label=high" in body
