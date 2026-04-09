"""Integration tests for the standalone ops case detail page."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from returns.models import CaseEvent, CaseNote, ReturnCase
from returns.services.cases import ReturnCaseWorkflowError
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
    assert "Quick navigation" in content
    assert "Jump between workflow, notes, documents, timeline, and case actions." in content
    assert "Operational workflow controls" in content
    assert "Apply status update" in content
    assert "Request information" in content
    assert "Save internal note" in content
    assert "Internal notes" in content
    assert 'id="case-status-panel"' in content
    assert 'data-loading-label="Updating workflow state"' in content
    assert 'id="case-notes-panel"' in content
    assert 'data-loading-label="Updating internal notes"' in content
    assert 'id="case-document-table"' in content
    assert 'data-loading-label="Updating case documents"' in content
    assert 'id="case-timeline"' in content
    assert 'data-loading-label="Updating audit timeline"' in content
    assert 'id="case-risk-panel"' in content
    assert 'data-loading-label="Updating risk summary"' in content
    assert 'id="case-action-panel"' in content
    assert 'data-loading-label="Updating case actions"' in content
    assert 'id="case-upload-panel"' in content
    assert 'data-loading-label="Updating upload panel"' in content
    assert (
        content.index("Workflow state")
        < content.index("Internal notes")
        < content.index("Documents")
    )


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
    assert "No notes yet" in content


@pytest.mark.django_db
def test_ops_case_detail_shows_notes_in_reverse_chronological_order(client) -> None:
    """Newest notes should appear first in the internal notes panel."""

    ops_user = UserFactory(email="ops-notes-order@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-NOTES-ORDER")
    first_note = CaseNote.objects.create(
        return_case=return_case,
        author=ops_user,
        body="Older note",
        is_internal=True,
    )
    second_note = CaseNote.objects.create(
        return_case=return_case,
        author=ops_user,
        body="Newer note",
        is_internal=True,
    )

    client.force_login(ops_user)
    response = client.get(reverse("ops:case-detail", kwargs={"case_id": return_case.pk}))

    content = response.content.decode()

    assert response.status_code == 200
    assert content.index(second_note.body) < content.index(first_note.body)


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
    assert "Internal notes" in payload["notes_panel_html"]


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
    event = CaseEvent.objects.get(return_case=return_case, event_type="status_updated")
    payload = response.json()

    assert response.status_code == 200
    assert return_case.status == ReturnCase.Status.WAITING_CUSTOMER
    assert "Requested additional information from customer" in note.body
    assert "Requested additional information from customer" in event.payload["note"]
    assert "Case moved to waiting on customer." in payload["action_panel_html"]
    assert "Waiting for customer" in payload["status_panel_html"]
    assert "Latest request" in payload["action_panel_html"]
    assert "Internal notes" in payload["notes_panel_html"]


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
    assert CaseEvent.objects.filter(return_case=return_case, event_type="note_added").count() == 1
    assert "Internal note added." in payload["notes_panel_html"]
    assert "note_added" in payload["timeline_html"].lower()
    assert "replacement stock is available" in payload["timeline_html"].lower()
    assert (
        "Merchant called back and confirmed replacement stock is available."
        in payload["notes_panel_html"]
    )


@pytest.mark.django_db
def test_ops_case_detail_status_update_invalid_submission_returns_local_form_errors(client) -> None:
    """Invalid status updates should stay inside the action panel."""

    ops_user = UserFactory(email="ops-status-invalid@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(
        order_reference="OPS-STATUS-INVALID",
        status=ReturnCase.Status.SUBMITTED,
    )

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "case-update",
            "status": ReturnCase.Status.SUBMITTED,
            "priority": ReturnCase.Priority.HIGH,
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    payload = response.json()

    assert response.status_code == 400
    assert "problem with this status update" in payload["action_panel_html"].lower()


@pytest.mark.django_db
def test_ops_case_detail_request_info_invalid_submission_returns_local_form_errors(client) -> None:
    """Invalid follow-up requests should stay inside the action panel."""

    ops_user = UserFactory(email="ops-request-invalid@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(
        order_reference="OPS-REQ-INVALID", status=ReturnCase.Status.IN_REVIEW
    )

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "request-info",
            "recipient": "customer",
            "message": "",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    payload = response.json()

    assert response.status_code == 400
    assert "problem with this follow-up request" in payload["action_panel_html"].lower()


@pytest.mark.django_db
def test_ops_case_detail_add_note_invalid_submission_returns_local_form_errors(client) -> None:
    """Invalid note submissions should stay inside the notes panel."""

    ops_user = UserFactory(email="ops-note-invalid@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-NOTE-INVALID")

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "add-note",
            "body": "",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    payload = response.json()

    assert response.status_code == 400
    assert "problem with this note" in payload["notes_panel_html"].lower()


@pytest.mark.django_db
def test_ops_case_detail_invalid_action_returns_local_error(client) -> None:
    """Unknown ops actions should return a local notes-panel error."""

    ops_user = UserFactory(email="ops-action-invalid@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-ACTION-INVALID")

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={"ops_action": "not-a-real-action"},
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    payload = response.json()

    assert response.status_code == 400
    assert "Choose a valid ops action." in payload["notes_panel_html"]


@pytest.mark.django_db
def test_ops_case_detail_post_blocks_authenticated_wrong_role(client) -> None:
    """Authenticated non-ops users should receive a 403 response on inline action posts."""

    customer_user = UserFactory(email="ops-post-customer@example.com")
    add_group(customer_user, "Customer")
    return_case = ReturnCaseFactory(order_reference="OPS-POST-FORBIDDEN")

    client.force_login(customer_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "add-note",
            "body": "Unauthorized note attempt.",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_ops_case_detail_request_info_workflow_errors_render_back_into_action_panel(
    client,
    monkeypatch,
) -> None:
    """Workflow service errors should be shown inside the same action panel."""

    ops_user = UserFactory(email="ops-request-error@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(
        order_reference="OPS-REQ-ERROR", status=ReturnCase.Status.APPROVED
    )

    monkeypatch.setattr(
        "console.views.update_return_case_status",
        lambda **kwargs: (_ for _ in ()).throw(
            ReturnCaseWorkflowError("Workflow rejected this update.")
        ),
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

    payload = response.json()

    assert response.status_code == 400
    assert "Workflow rejected this update." in payload["action_panel_html"]


@pytest.mark.django_db
def test_ops_case_detail_non_ajax_post_renders_updated_page(client, monkeypatch) -> None:
    """Non-AJAX submissions should render the full page with success state."""

    ops_user = UserFactory(email="ops-note-html@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-NOTE-HTML")

    client.force_login(ops_user)
    response = client.post(
        reverse("ops:case-detail", kwargs={"case_id": return_case.pk}),
        data={
            "ops_action": "add-note",
            "body": "Ops reviewed the case and is waiting on warehouse confirmation.",
        },
    )

    content = response.content.decode()

    assert response.status_code == 200
    assert "Internal note added." in content
    assert "Ops reviewed the case and is waiting on warehouse confirmation." in content
