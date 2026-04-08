# path: tests/test_ops_actions.py
"""Integration tests for HTMX ops workflow actions."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.returns.models import CaseEvent, CaseNote
from tests.factories.accounts import UserFactory
from tests.factories.returns import ReturnCaseFactory


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_can_update_case_workflow_and_emit_event(client):
    """A valid HTMX workflow update should persist and create an audit event."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory(status="submitted", priority="normal")

    response = client.post(
        reverse("ops:case-update", args=[case.pk]),
        {"status": "in_review", "priority": "high"},
        HTTP_HX_REQUEST="true",
    )

    case.refresh_from_db()

    assert response.status_code == 200
    assert case.status == "in_review"
    assert case.priority == "high"
    assert CaseEvent.objects.filter(case=case, event_type="ops_case_updated").exists()


@pytest.mark.django_db()
def test_ops_case_update_returns_422_for_invalid_form(client):
    """Invalid HTMX workflow updates should render a 422 response."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.post(
        reverse("ops:case-update", args=[case.pk]),
        {"status": "", "priority": ""},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 422
    assert "This field is required." in response.content.decode()


@pytest.mark.django_db()
def test_ops_can_request_more_information(client):
    """Ops should be able to record a request for more information."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.post(
        reverse("ops:request-info", args=[case.pk]),
        {"recipient": "customer", "message": "Please upload a clearer delivery damage photo."},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert CaseEvent.objects.filter(case=case, event_type="info_requested").exists()


@pytest.mark.django_db()
def test_ops_can_add_internal_note(client):
    """Ops should be able to persist internal notes from the detail page."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()

    response = client.post(
        reverse("ops:add-note", args=[case.pk]),
        {"body": "Customer appears responsive. Await merchant packaging confirmation."},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert CaseNote.objects.filter(case=case).count() == 1
    assert CaseEvent.objects.filter(case=case, event_type="note_added").exists()


@pytest.mark.django_db()
def test_wrong_role_cannot_post_to_ops_actions(client):
    """Authenticated non-ops users should receive 403 responses from HTMX endpoints."""
    customer_user = UserFactory()
    _add_group(customer_user, "customer")
    client.force_login(customer_user)

    case = ReturnCaseFactory()

    response = client.post(
        reverse("ops:add-note", args=[case.pk]),
        {"body": "Unauthorised note attempt"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 403
