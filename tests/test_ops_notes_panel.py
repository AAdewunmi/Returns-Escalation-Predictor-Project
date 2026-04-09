# path: tests/test_ops_notes_panel.py
"""Integration tests for ops detail layout and notes rendering."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories.accounts import UserFactory
from tests.factories.returns import CaseNoteFactory, ReturnCaseFactory


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_detail_renders_notes_panel_and_action_bar(client):
    """The detail page should expose the notes panel and action bar."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.get(reverse("ops:case-detail", args=[case.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Action bar" in content
    assert "Internal notes" in content


@pytest.mark.django_db()
def test_ops_detail_shows_notes_in_reverse_chronological_order(client):
    """Newest notes should appear first in the notes panel."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()
    first_note = CaseNoteFactory(case=case, body="Older note")
    second_note = CaseNoteFactory(case=case, body="Newer note")

    response = client.get(reverse("ops:case-detail", args=[case.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert content.index(second_note.body) < content.index(first_note.body)


@pytest.mark.django_db()
def test_ops_detail_shows_empty_note_state_when_no_notes_exist(client):
    """Sparse cases should still render a deliberate note-panel empty state."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.get(reverse("ops:case-detail", args=[case.pk]))

    assert response.status_code == 200
    assert "No notes yet" in response.content.decode()
