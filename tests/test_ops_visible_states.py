# path: tests/test_ops_visible_states.py
"""Integration tests for visible queue and detail states on the ops surface."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories.accounts import UserFactory
from tests.factories.returns import MerchantProfileFactory, ReturnCaseFactory


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_queue_shows_empty_state_when_no_cases_match(client):
    """A filter that matches no rows should render the shared empty state."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    ReturnCaseFactory(status="submitted")

    response = client.get(reverse("ops:queue"), {"status": "closed"})

    assert response.status_code == 200
    assert "No cases match these filters" in response.content.decode()


@pytest.mark.django_db()
def test_ops_queue_page_two_renders_when_case_count_exceeds_page_size(client):
    """The queue should expose a second page once enough cases exist."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    merchant = MerchantProfileFactory()

    for index in range(16):
        ReturnCaseFactory(reference=f"RC-P2-{index:04d}", merchant=merchant)

    response = client.get(reverse("ops:queue"), {"page": "2"})

    assert response.status_code == 200
    assert response.context["page_obj"].number == 2


@pytest.mark.django_db()
def test_ops_detail_sparse_case_keeps_evidence_and_timeline_empty_states(client):
    """Sparse cases should render both evidence and timeline empty-state components."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.get(reverse("ops:case-detail", args=[case.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "No evidence yet" in content
    assert "No audit events yet" in content
