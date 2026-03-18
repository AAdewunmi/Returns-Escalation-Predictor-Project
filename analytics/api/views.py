# path: analytics/api/views.py
"""API views for ReturnHub analytics endpoints."""

from __future__ import annotations

from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.services.return_metrics import (
    ReturnMetricsError,
    ReturnMetricsWindow,
    build_return_metrics,
)
from returns.api.permissions import IsOpsOrAdmin


class ReturnAnalyticsAPIView(APIView):
    """Return bounded return metrics for ops and admins."""

    permission_classes = [IsAuthenticated, IsOpsOrAdmin]

    def get(self, request, *args, **kwargs):
        """Aggregate return metrics for the supplied date window."""
        try:
            from_date = date.fromisoformat(request.query_params["from"])
            to_date = date.fromisoformat(request.query_params["to"])
        except KeyError as exc:
            return Response(
                {"detail": f"Missing required query parameter: {exc.args[0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError:
            return Response(
                {"detail": "Dates must use ISO format YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = build_return_metrics(
                window=ReturnMetricsWindow(from_date=from_date, to_date=to_date)
            )
        except ReturnMetricsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(payload, status=status.HTTP_200_OK)
