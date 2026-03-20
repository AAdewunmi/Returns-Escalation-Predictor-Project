# path: tests/test_ops_console_shell.py
"""Integration tests for the ops console risk shell presentation."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from tests.factories import ReturnCaseFactory, UserFactory


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_console_includes_risk_explainer_panel(client) -> None:
    """Ops shell should explain risk as a controlled triage signal."""
    ops_user = UserFactory(email="ops-console-risk@example.com")
    add_group(ops_user, "ops")
    ReturnCaseFactory.create_batch(2, status="submitted")

    client.force_login(ops_user)
    response = client.get("/console/ops/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "escalation risk remains" in content
    assert "ops only" in content
    assert "controlled triage signal" in content
