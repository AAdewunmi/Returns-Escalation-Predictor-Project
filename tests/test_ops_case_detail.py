"""Integration tests for the standalone ops case detail page."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from returns.models import CaseNote, ReturnCase
from tests.factories import (
    CaseEventFactory,
    EvidenceDocumentFactory,
    ReturnCaseFactory,
    RiskScoreFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""

    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_case_detail_renders_documents_timeline_and_risk(client) -> None:
    """Ops users should be able to inspect the full case detail page."""

    ops_user = UserFactory(email="ops-detail@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-DETAIL-200")
    EvidenceDocumentFactory(return_case=return_case, original_filename="photo-proof.jpg")
    RiskScoreFactory(
        case=return_case,
        label="high",
        score="0.82",
        reason_codes=["long_message", "high_value_order"],
    )
    CaseEventFactory(return_case=return_case, event_type="document_uploaded", actor=ops_user)

    client.force_login(ops_user)
    response = client.get(reverse("ops:case-detail", kwargs={"case_id": return_case.pk}))

    content = response.content.decode()

    assert response.status_code == 200
    assert "OPS-DETAIL-200" in content
    assert "photo-proof.jpg" in content
    assert "Escalation risk" in content
    assert "Timeline" in content
    assert "Operational workflow controls" in content
    assert "Apply status update" in content
    assert "Request information" in content
    assert "Save internal note" in content


@pytest.mark.django_db
def test_ops_case_detail_blocks_authenticated_wrong_role(client) -> None:
    """Authenticated non-ops users should receive a 403 response."""

    customer_user = UserFactory(email="ops-detail-customer@example.com")
    add_group(customer_user, "Customer")
    return_case = ReturnCaseFactory()

    client.force_login(customer_user)
    response = client.get(reverse("ops:case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 403
    assert "Forbidden" in response.content.decode()


@pytest.mark.django_db
def test_ops_case_detail_returns_404_for_missing_case(client) -> None:
    """Unknown case identifiers should return a 404 response."""

    ops_user = UserFactory(email="ops-missing-case@example.com")
    add_group(ops_user, "Ops")

    client.force_login(ops_user)
    response = client.get(reverse("ops:case-detail", kwargs={"case_id": 999999}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_ops_case_detail_shows_current_empty_states_when_case_is_sparse(client) -> None:
    """The page should remain readable when documents, events, and risk are absent."""

    ops_user = UserFactory(email="ops-empty-case@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-EMPTY-1")

    client.force_login(ops_user)
    response = client.get(reverse("ops:case-detail", kwargs={"case_id": return_case.pk}))

    content = response.content.decode()

    assert response.status_code == 200
    assert "No documents yet" in content
    assert "No timeline events yet" in content
    assert "No score yet" in content


@pytest.mark.django_db
def test_ops_case_detail_status_update_post_refreshes_inline_fragments(client, monkeypatch) -> None:
    """Posting a status update should refresh the ops fragments and persist the change."""

    ops_user = UserFactory(email="ops-status-update@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(
        order_reference="OPS-STATUS-1",
        status=ReturnCase.Status.SUBMITTED,
        priority=ReturnCase.Priority.MEDIUM,
    )
    monkeypatch.setattr(
        "returns.services.cases.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "case-update",
            "status": ReturnCase.Status.IN_REVIEW,
            "priority": ReturnCase.Priority.HIGH,
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    return_case.refresh_from_db()
    payload = response.json()

    assert response.status_code == 200
    assert return_case.status == ReturnCase.Status.IN_REVIEW
    assert return_case.priority == ReturnCase.Priority.HIGH
    assert "Case status updated." in payload["action_panel_html"]
    assert "In review" in payload["status_panel_html"]
    assert "High" in payload["status_panel_html"]


@pytest.mark.django_db
def test_ops_case_detail_request_info_post_moves_case_to_waiting_state(client, monkeypatch) -> None:
    """Posting a request-for-info should use the canonical waiting status flow."""

    ops_user = UserFactory(email="ops-request-info@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(
        order_reference="OPS-WAIT-1",
        status=ReturnCase.Status.IN_REVIEW,
    )
    monkeypatch.setattr(
        "returns.services.cases.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "request-info",
            "recipient": "customer",
            "message": "Please upload a clearer photo of the damaged item.",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    return_case.refresh_from_db()
    note = CaseNote.objects.get(return_case=return_case)
    payload = response.json()

    assert response.status_code == 200
    assert return_case.status == ReturnCase.Status.WAITING_CUSTOMER
    assert "Requested additional information from customer" in note.body
    assert "Case moved to waiting on customer." in payload["action_panel_html"]
    assert "Waiting for customer" in payload["status_panel_html"]


@pytest.mark.django_db
def test_ops_case_detail_add_note_post_refreshes_timeline(client) -> None:
    """Posting an internal note should persist it and refresh the timeline fragment."""

    ops_user = UserFactory(email="ops-note@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-NOTE-1")

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "add-note",
            "body": "Merchant called back and confirmed replacement stock is available.",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    payload = response.json()

    assert response.status_code == 200
    assert CaseNote.objects.filter(return_case=return_case).count() == 1
    assert "Internal note added." in payload["action_panel_html"]
    assert "note_added" in payload["timeline_html"].lower()
    assert "replacement stock is available" in payload["timeline_html"].lower()
