# path: tests/test_case_detail_evidence_views.py
"""
Integration tests for the case detail evidence workspace.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.returns.models import EvidenceDocumentKind
from apps.returns.tests.factories import EvidenceDocumentFactory, ReturnCaseFactory, RiskScoreFactory, UserFactory


@pytest.mark.django_db
def test_case_detail_renders_documents_and_risk_summary(client):
    """
    Case detail page should render uploaded documents and latest risk.
    """

    return_case = ReturnCaseFactory()
    ops_user = UserFactory()
    Group.objects.get_or_create(name="ops")[0].user_set.add(ops_user)
    EvidenceDocumentFactory(return_case=return_case, original_filename="receipt.pdf", content_type="application/pdf")
    RiskScoreFactory(return_case=return_case, score="0.8100", label="high")
    client.force_login(ops_user)

    response = client.get(reverse("web-case-detail", args=[return_case.id]))

    assert response.status_code == 200
    assert "receipt.pdf" in response.content.decode()
    assert "Escalation risk" in response.content.decode()


@pytest.mark.django_db
def test_case_detail_forbidden_for_unrelated_customer(client):
    """
    Wrong customer should receive a forbidden response.
    """

    return_case = ReturnCaseFactory()
    other_user = UserFactory()
    Group.objects.get_or_create(name="customer")[0].user_set.add(other_user)
    client.force_login(other_user)

    response = client.get(reverse("web-case-detail", args=[return_case.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_upload_panel_returns_validation_errors_for_missing_file(client):
    """
    Invalid HTMX upload should return the upload partial with status 422.
    """

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)
    client.force_login(customer_user)

    response = client.post(
        reverse("web-case-document-upload", args=[return_case.id]),
        {
            "document_kind": EvidenceDocumentKind.CUSTOMER_EVIDENCE,
            "note": "Missing file should fail validation",
        },
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 422
    assert "problem with this upload" in response.content.decode().lower()


@pytest.mark.django_db
def test_customer_can_upload_document_from_case_detail(client, monkeypatch):
    """
    Valid upload should redirect back to case detail.
    """

    monkeypatch.setattr(
        "apps.returns.services.risk.score_case_for_escalation",
        lambda **kwargs: None,
        raising=False,
    )

    return_case = ReturnCaseFactory()
    customer_user = return_case.customer_profile.user
    Group.objects.get_or_create(name="customer")[0].user_set.add(customer_user)
    client.force_login(customer_user)

    response = client.post(
        reverse("web-case-document-upload", args=[return_case.id]),
        {
            "document_kind": EvidenceDocumentKind.CUSTOMER_EVIDENCE,
            "file": SimpleUploadedFile("photo.jpg", b"jpg", content_type="image/jpeg"),
            "note": "Front panel damage",
        },
    )

    assert response.status_code == 302
