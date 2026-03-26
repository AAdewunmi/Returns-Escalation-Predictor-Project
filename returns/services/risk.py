# path: returns/services/risk.py
"""Risk-persistence services linking the returns and ML domains."""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from ml.features import extract_case_features
from ml.scoring import score_case_features
from ml.services.scoring import ArtifactScoringUnavailableError
from ml.services.scoring import score_return_case as score_ml_return_case
from returns.models import CaseEvent, ReturnCase, RiskScore

logger = logging.getLogger(__name__)


def _get_scoring_result(return_case: ReturnCase):
    """Prefer artefact-backed scoring and fall back to the placeholder scorer."""

    try:
        return score_ml_return_case(return_case)
    except ArtifactScoringUnavailableError:
        logger.warning("Falling back to placeholder risk scoring for case_id=%s", return_case.pk)
        features = extract_case_features(return_case)
        return score_case_features(features)


@transaction.atomic
def score_case_and_persist(
    return_case: ReturnCase,
    *,
    triggered_by: str,
) -> RiskScore:
    """
    Score a case and persist the resulting RiskScore record.

    The current schema stores one RiskScore per case. Re-scoring updates the
    current record and emits a fresh audit event.
    """

    scoring_result = _get_scoring_result(return_case)

    risk_score, _ = RiskScore.objects.update_or_create(
        case=return_case,
        defaults={
            "model_version": scoring_result.model_version,
            "score": scoring_result.score,
            "label": scoring_result.label,
            "reason_codes": scoring_result.reason_codes,
            "scored_at": timezone.now(),
        },
    )

    CaseEvent.objects.create(
        return_case=return_case,
        actor=None,
        actor_role="",
        event_type="risk_scored",
        payload={
            "triggered_by": triggered_by,
            "model_version": scoring_result.model_version,
            "label": scoring_result.label,
            "score": str(scoring_result.score),
            "reason_codes": scoring_result.reason_codes,
        },
    )

    return risk_score
