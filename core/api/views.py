"""Operational API views for ReturnHub core endpoints."""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.health import get_readiness_payload


class HealthCheckView(APIView):
    """Expose a small readiness contract for load balancers and probes."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs) -> Response:
        """Return the current readiness state for the application."""
        payload = get_readiness_payload()
        response_status = (
            status.HTTP_200_OK
            if payload["status"] == "ok"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=response_status)
