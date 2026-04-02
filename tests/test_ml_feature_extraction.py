# path: tests/test_ml_feature_extraction.py
"""
Tests for evidence-aware feature extraction.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.returns.ml.feature_extraction import extract_case_feature_vector, load_feature_names
from apps.returns.models import EvidenceDocumentKind
from apps.returns.tests.factories import EvidenceDocumentFactory, ReturnCaseFactory


@pytest.mark.django_db
def test_feature_extraction_preserves_contract_order_when_no_evidence():
    """
    Feature extraction should keep the same ordered feature list even without documents.
    """

    return_case = ReturnCaseFactory()
    features = extract_case_feature_vector(return_case)

    assert list(features.keys()) == load_feature_names()
    assert features["evidence_count"] == 0.0
    assert features["has_image_evidence"] == 0.0
    assert features["hours_to_first_customer_evidence"] == 0.0


@pytest.mark.django_db
def test_feature_extraction_uses_evidence_metadata_deterministically():
    """
    Evidence metadata should map to stable numeric features.
    """

    return_case = ReturnCaseFactory(opened_at=timezone.now() - timezone.timedelta(hours=10))
    EvidenceDocumentFactory(
        return_case=return_case,
        document_kind=EvidenceDocumentKind.CUSTOMER_EVIDENCE,
        content_type="application/pdf",
        size_bytes=2048,
    )

    features = extract_case_feature_vector(return_case)

    assert features["evidence_count"] == 1.0
    assert features["customer_evidence_count"] == 1.0
    assert features["has_pdf_evidence"] == 1.0
    assert features["evidence_total_size_kb"] == 2.0
