# path: returns/services/risk.py
"""Risk-persistence services linking the returns and ML domains."""

from __future__ import annotations

from django.db import transaction

from apps.ml.models import RiskScore
from apps.ml.services.scoring import score_return_case
from apps.returns.models import CaseEvent, ReturnCase


@transaction.atomic
def score_case_and_persist(
    return_case: ReturnCase,
    *,
    triggered_by: str,
) -> RiskScore:
    """
    Score a case and persist the resulting RiskScore record.

    Risk scores are append-only so historical scoring output can be audited.
    The latest record is the current risk view used by queue and detail surfaces.
    """

    scoring_result = score_return_case(return_case)

    risk_score = RiskScore.objects.create(
        return_case=return_case,
        model_version=scoring_result.model_version,
        feature_contract_hash=scoring_result.feature_contract_hash,
        reason_code_schema_version=scoring_result.reason_code_schema_version,
        score=scoring_result.score,
        label=scoring_result.label,
        reason_codes=scoring_result.reason_codes,
    )

    CaseEvent.objects.create(
        return_case=return_case,
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
