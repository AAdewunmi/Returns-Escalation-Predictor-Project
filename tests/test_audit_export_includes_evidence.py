# path: tests/test_audit_export_includes_evidence.py
"""Tests for evidence-aware audit export."""

from __future__ import annotations

import pytest

from returns.services.audit_export import build_return_case_audit_csv
from tests.factories import (
    EvidenceDocumentFactory,
    ReturnCaseFactory,
    RiskScoreFactory,
)


@pytest.mark.django_db
def test_audit_export_contains_document_and_risk_rows() -> None:
    """Audit export should include evidence metadata and latest risk values."""

    return_case = ReturnCaseFactory()
    EvidenceDocumentFactory(
        return_case=return_case,
        original_filename="photo.jpg",
        content_type="image/jpeg",
    )
    RiskScoreFactory(
        case=return_case,
        score="0.73",
        label="medium",
        reason_codes=["missing_customer_evidence"],
    )

    csv_output = build_return_case_audit_csv(return_case)

    assert "photo.jpg" in csv_output
    assert "image/jpeg" in csv_output
    assert "order_reference" in csv_output
    assert "0.73" in csv_output
    assert "missing_customer_evidence" in csv_output


@pytest.mark.django_db
def test_audit_export_handles_case_without_risk_or_documents() -> None:
    """Audit export should still emit case rows when no risk, events, or documents exist."""

    return_case = ReturnCaseFactory(order_reference="AUDIT-EMPTY-001")

    csv_output = build_return_case_audit_csv(return_case)

    assert "section,key,value" in csv_output
    assert "case,order_reference,AUDIT-EMPTY-001" in csv_output
    assert "risk,score" not in csv_output
    assert "document,kind" not in csv_output
