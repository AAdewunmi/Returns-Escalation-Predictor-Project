# path: tests/test_ops_surface_smoke.py
"""Smoke tests for the ops queue and detail surfaces."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories.accounts import UserFactory
from tests.factories.returns import ReturnCaseFactory


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_queue_smoke(client):
    """The queue should load for an ops user."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    ReturnCaseFactory()

    response = client.get(reverse("ops:queue"))

    assert response.status_code == 200
    assert "Returns queue" in response.content.decode()


@pytest.mark.django_db()
def test_ops_detail_smoke(client):
    """The detail page should load for an ops user."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.get(reverse("ops:case-detail", args=[case.pk]))

    assert response.status_code == 200
    assert case.reference in response.content.decode()
