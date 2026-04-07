# path: returns/services/ops_case_detail.py
"""Detail-page context builders for the ops surface."""

from __future__ import annotations

from typing import Any

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.returns.models import CaseEvent, EvidenceDocument, ReturnCase, RiskScore


def build_ops_case_detail_context(case_id: str) -> dict[str, Any]:
    """Load a case and its related operational data for the ops detail page."""
    case = get_object_or_404(
        ReturnCase.objects.select_related(
            "customer",
            "customer__user",
            "merchant",
        ).prefetch_related(
            Prefetch(
                "evidence_documents",
                queryset=EvidenceDocument.objects.order_by("-created_at"),
            ),
            Prefetch(
                "events",
                queryset=CaseEvent.objects.select_related("actor").order_by("-created_at"),
            ),
            Prefetch(
                "risk_scores",
                queryset=RiskScore.objects.order_by("-created_at"),
                to_attr="prefetched_risk_scores",
            ),
        ),
        pk=case_id,
    )

    latest_risk = case.prefetched_risk_scores[0] if case.prefetched_risk_scores else None

    return {
        "case": case,
        "latest_risk": latest_risk,
        "documents": list(case.evidence_documents.all()),
        "events": list(case.events.all()),
    }
