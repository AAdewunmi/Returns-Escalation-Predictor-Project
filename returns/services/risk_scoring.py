# path: returns/services/risk_scoring.py
"""Risk score persistence for ReturnHub return cases."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from ml.features import extract_case_features
from ml.scoring import score_case_features
from returns.models import CaseEvent, RiskScore


@transaction.atomic
def score_return_case(case) -> RiskScore:
    """Extract deterministic features, score the case, and persist RiskScore."""
    features = extract_case_features(case)
    prediction = score_case_features(features)

    risk_score, _ = RiskScore.objects.update_or_create(
        case=case,
        defaults={
            "model_version": prediction.model_version,
            "score": prediction.score,
            "label": prediction.label,
            "reason_codes": prediction.reason_codes,
            "scored_at": timezone.now(),
        },
    )

    CaseEvent.objects.create(
        case=case,
        actor=None,
        event_type="risk_scored",
        description="Placeholder escalation risk persisted for case.",
        metadata={
            "model_version": prediction.model_version,
            "label": prediction.label,
            "score": str(prediction.score),
        },
    )
    return risk_score
