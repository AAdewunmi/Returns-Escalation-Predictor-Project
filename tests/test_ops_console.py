# path: tests/test_ops_console.py
"""Surface tests for the ops console queue preview."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from returns.models import RiskScore
from tests.factories import ReturnCaseFactory, UserFactory


def _ops_user():
    """Create a user with ops console access."""

    user = UserFactory()
    ops_group, _ = Group.objects.get_or_create(name="Ops")
    user.groups.add(ops_group)
    return user


@pytest.mark.django_db
def test_ops_console_renders_page_two_and_preserves_filters(client) -> None:
    """The ops console should render paginated results and preserve active filters."""

    for index in range(18):
        case = ReturnCaseFactory(
            status="submitted",
            order_reference=f"ORD-{4000 + index}",
        )
        RiskScore.objects.create(
            case=case,
            model_version="baseline-v1",
            score="0.82",
            label="high",
            reason_codes=["PRIOR_RETURNS_HIGH"],
            scored_at=timezone.now(),
        )

    client.force_login(_ops_user())

    response = client.get(
        reverse("console:ops-dashboard"),
        {"status": "submitted", "page": 2},
    )

    body = response.content.decode()

    assert response.status_code == 200
    assert "Showing 16-18 of 18" in body
    assert '?status=submitted&amp;page=1' in body or "?page=1&amp;status=submitted" in body
    assert "High risk" in body


@pytest.mark.django_db
def test_ops_console_returns_forbidden_for_wrong_role(client) -> None:
    """Authenticated users without ops access should see a clean forbidden response."""

    client.force_login(UserFactory())

    response = client.get(reverse("console:ops-dashboard"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_ops_console_empty_state_renders(client) -> None:
    """An empty queue should render the shared empty-state pattern."""

    client.force_login(_ops_user())

    response = client.get(reverse("console:ops-dashboard"))

    assert response.status_code == 200
    assert "No cases match these filters" in response.content.decode()
