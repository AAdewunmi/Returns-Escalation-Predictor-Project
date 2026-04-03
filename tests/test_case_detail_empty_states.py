# path: tests/test_case_detail_empty_states.py
"""Tests for deliberate empty states on case detail pages."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from tests.factories import ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_case_detail_renders_empty_document_and_no_score_states(client) -> None:
    """Empty-state messaging should render cleanly when no documents or risk exist."""

    return_case = ReturnCaseFactory()
    ops_user = UserFactory()
    Group.objects.get_or_create(name="ops")[0].user_set.add(ops_user)
    client.force_login(ops_user)

    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.id}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "No documents yet" in content
    assert "No score yet" in content
    assert "No timeline events yet" in content
