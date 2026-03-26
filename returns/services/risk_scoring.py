# path: returns/services/risk_scoring.py
"""Risk score persistence for ReturnHub return cases."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ml.features import extract_case_features
from ml.scoring import score_case_features
from ml.services.scoring import ArtifactScoringUnavailableError
from ml.services.scoring import score_return_case as score_active_model
from returns.models import CaseEvent, RiskScore

logger = logging.getLogger(__name__)


def _get_prediction_for_case(case):
    """Prefer the active artefact-backed scorer and fall back to the placeholder scorer."""

    try:
        return score_active_model(case)
    except ArtifactScoringUnavailableError:
        logger.warning("Falling back to placeholder risk scoring for case_id=%s", case.pk)
        features = extract_case_features(case)
        return score_case_features(features)


@transaction.atomic
def score_return_case(case) -> RiskScore:
    """Score the case, persist RiskScore, and emit a matching event."""
    prediction = _get_prediction_for_case(case)

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
        return_case=case,
        actor=None,
        actor_role="",
        event_type="risk_scored",
        payload={
            "model_version": prediction.model_version,
            "label": prediction.label,
            "score": str(prediction.score),
        },
    )
    return risk_score
