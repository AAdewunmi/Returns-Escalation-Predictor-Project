# path: tests/test_return_detail_includes_evidence_and_risk.py
"""Integration tests for the return detail API projection."""

from __future__ import annotations

import pytest

from api.serializers.returns import ReturnCaseDetailSerializer
from tests.factories import (
    EvidenceDocumentFactory,
    ReturnCaseFactory,
    RiskScoreFactory,
)


@pytest.mark.django_db
def test_return_detail_serializer_embeds_documents_and_latest_risk() -> None:
    """Detail serializer should include evidence metadata and latest risk summary."""

    return_case = ReturnCaseFactory()
    EvidenceDocumentFactory(
        return_case=return_case,
        original_filename="evidence.pdf",
        content_type="application/pdf",
    )
    RiskScoreFactory(case=return_case, score="0.66", label="medium")

    payload = ReturnCaseDetailSerializer(return_case).data

    assert payload["documents"][0]["original_filename"] == "evidence.pdf"
    assert payload["latest_risk"]["label"] == "medium"


@pytest.mark.django_db
def test_return_detail_serializer_returns_empty_documents_and_null_risk() -> None:
    """Detail serializer should return stable empty values when no documents or risk exist."""

    return_case = ReturnCaseFactory()

    payload = ReturnCaseDetailSerializer(return_case).data

    assert payload["documents"] == []
    assert payload["latest_risk"] is None
