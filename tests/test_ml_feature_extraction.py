# path: tests/test_ml_feature_extraction.py
"""Focused tests for evidence-aware feature extraction helpers."""

from __future__ import annotations

import datetime
from collections import OrderedDict

import pytest

from ml.features import build_feature_vector, extract_case_features, load_feature_contract
from returns.models import EvidenceDocument
from tests.factories import EvidenceDocumentFactory, ReturnCaseFactory


def test_build_feature_vector_matches_committed_contract_order() -> None:
    """Primitive feature building should follow the committed contract exactly."""

    features = build_feature_vector(
        item_category="electronics",
        delivery_to_return_days=5,
        return_reason="damaged",
        customer_message="Customer included a detailed evidence summary.",
        prior_returns_count=2,
        order_value="450.00",
        evidence_count=1,
        hours_to_first_customer_evidence=12.0,
        merchant_document_count=0,
    )

    contract = load_feature_contract()

    assert isinstance(features, OrderedDict)
    assert list(features.keys()) == contract["feature_names"]
    assert features["return_reason_is_damaged"] == 1
    assert features["order_value_band_high"] == 1


@pytest.mark.django_db
def test_extract_case_features_emits_zero_evidence_signals_without_documents() -> None:
    """Cases without documents should emit stable zero-valued evidence features."""

    case = ReturnCaseFactory()

    features = extract_case_features(case)

    assert features["evidence_count"] == 0
    assert features["hours_to_first_customer_evidence"] == 0.0
    assert features["merchant_document_count"] == 0


@pytest.mark.django_db
def test_extract_case_features_uses_document_metadata_deterministically() -> None:
    """Customer and merchant documents should map into stable evidence features."""

    case = ReturnCaseFactory()
    customer_document = EvidenceDocumentFactory(
        return_case=case,
        actor_role=EvidenceDocument.ActorRole.CUSTOMER,
        kind=EvidenceDocument.DocumentKind.EVIDENCE,
    )
    merchant_document = EvidenceDocumentFactory(
        return_case=case,
        uploaded_by=case.merchant.user,
        actor_role=EvidenceDocument.ActorRole.MERCHANT,
        kind=EvidenceDocument.DocumentKind.RESPONSE,
        original_filename="merchant-response.pdf",
        content_type="application/pdf",
    )

    case.created_at = datetime.datetime(2026, 4, 2, 9, 0, tzinfo=datetime.UTC)
    case.save(update_fields=["created_at"])
    EvidenceDocument.objects.filter(pk=customer_document.pk).update(
        created_at=datetime.datetime(2026, 4, 2, 15, 0, tzinfo=datetime.UTC)
    )
    EvidenceDocument.objects.filter(pk=merchant_document.pk).update(
        created_at=datetime.datetime(2026, 4, 2, 16, 0, tzinfo=datetime.UTC)
    )

    features = extract_case_features(case)

    assert features["evidence_count"] == 1
    assert features["merchant_document_count"] == 1
    assert features["hours_to_first_customer_evidence"] == 6.0
