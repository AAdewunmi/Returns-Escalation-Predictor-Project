# path: api/serializers/returns.py
"""Compatibility exports for the canonical return-case serializers."""

from returns.api.serializers import ReturnCaseDetailSerializer
from returns.api.serializers import RiskScoreSerializer as RiskSummarySerializer

__all__ = ["ReturnCaseDetailSerializer", "RiskSummarySerializer"]
