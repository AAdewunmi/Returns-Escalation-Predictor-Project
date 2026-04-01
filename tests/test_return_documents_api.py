"""Tests for the current returns documents API routing state."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories import ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_live_returns_documents_get_endpoint_is_not_registered() -> None:
    """The main returns API should not expose a documents GET route yet."""
    client = APIClient()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    client.force_authenticate(user=actor)

    response = client.get(f"/api/returns/{return_case.pk}/documents/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_live_returns_documents_post_endpoint_is_not_registered() -> None:
    """The main returns API should not expose a documents POST route yet."""
    client = APIClient()
    actor = UserFactory()
    return_case = ReturnCaseFactory()
    client.force_authenticate(user=actor)

    response = client.post(
        f"/api/returns/{return_case.pk}/documents/",
        data={},
        format="multipart",
    )

    assert response.status_code == 404
