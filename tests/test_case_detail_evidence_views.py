"""Integration tests for the case detail evidence workspace."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from returns.models import EvidenceDocument
from tests.factories import (
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
def test_case_detail_renders_documents_and_risk_summary(client) -> None:
    """Case detail should render uploaded documents and latest risk output."""

    return_case = ReturnCaseFactory(order_reference="CASE-EVID-001")
    ops_user = UserFactory()
    add_group(ops_user, "ops")
    EvidenceDocumentFactory(
        return_case=return_case,
        original_filename="receipt.pdf",
        content_type="application/pdf",
    )
    RiskScoreFactory(case=return_case, score="0.8100", label="high")

    client.force_login(ops_user)
    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 200
    assert "receipt.pdf" in response.content.decode()
    assert "Escalation risk" in response.content.decode()


@pytest.mark.django_db
def test_unrelated_customer_gets_403_on_case_detail(client) -> None:
    """An unrelated customer should not be able to access the case detail page."""

    return_case = ReturnCaseFactory(order_reference="CASE-EVID-002")
    other_user = UserFactory()
    add_group(other_user, "customer")

    client.force_login(other_user)
    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 403


@pytest.mark.django_db
def test_unrelated_merchant_gets_403_on_case_detail(client) -> None:
    """An unrelated merchant should not be able to access the case detail page."""

    return_case = ReturnCaseFactory(order_reference="CASE-EVID-005")
    other_user = UserFactory()
    add_group(other_user, "merchant")

    client.force_login(other_user)
    response = client.get(reverse("case-detail", kwargs={"case_id": return_case.pk}))

    assert response.status_code == 403


@pytest.mark.django_db
def test_upload_panel_returns_validation_errors_for_missing_file(client) -> None:
    """Invalid inline uploads should return local upload-panel errors."""

    return_case = ReturnCaseFactory(order_reference="CASE-EVID-003")
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")

    client.force_login(customer_user)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        {
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "notes": "Missing file should fail validation",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 400
    payload = response.json()
    assert "problem with this upload" in payload["upload_panel_html"].lower()
    assert "No documents yet" in payload["document_table_html"]


@pytest.mark.django_db
def test_customer_can_upload_document_from_case_detail(client, monkeypatch) -> None:
    """Valid inline uploads should refresh the document section with the new file."""

    monkeypatch.setattr(
        "returns.services.documents.score_case_and_persist",
        lambda *args, **kwargs: None,
    )

    return_case = ReturnCaseFactory(order_reference="CASE-EVID-004")
    customer_user = return_case.customer.user
    add_group(customer_user, "customer")

    client.force_login(customer_user)
    response = client.post(
        reverse("case-document-upload", kwargs={"case_id": return_case.pk}),
        {
            "kind": EvidenceDocument.DocumentKind.EVIDENCE,
            "file": SimpleUploadedFile("photo.jpg", b"jpg", content_type="image/jpeg"),
            "notes": "Front panel damage",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Document uploaded successfully." in payload["upload_panel_html"]
    assert "photo.jpg" in payload["document_table_html"]
