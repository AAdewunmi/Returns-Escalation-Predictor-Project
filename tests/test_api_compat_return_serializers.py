"""Tests for compatibility exports in api.serializers.returns."""

from api.serializers.returns import (
    ReturnCaseDetailSerializer,
    RiskSummarySerializer,
)
from returns.api.serializers import (
    ReturnCaseDetailSerializer as CanonicalReturnCaseDetailSerializer,
)
from returns.api.serializers import RiskScoreSerializer


def test_returns_serializer_compat_exports_point_to_canonical_serializers() -> None:
    """Compatibility imports should expose the canonical serializer classes."""

    assert ReturnCaseDetailSerializer is CanonicalReturnCaseDetailSerializer
    assert RiskSummarySerializer is RiskScoreSerializer
