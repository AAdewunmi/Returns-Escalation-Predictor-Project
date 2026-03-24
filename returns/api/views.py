# path: returns/api/views.py
"""DRF views for the ReturnHub return workflow."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.pagination import ContractPageNumberPagination
from returns.api.permissions import (
    IsCustomerOrAdmin,
    IsOpsOrAdmin,
    is_admin,
    is_ops,
    user_can_access_case,
)
from returns.api.serializers import (
    CaseNoteCreateSerializer,
    CaseNoteSerializer,
    OpsQueueItemSerializer,
    ReturnCaseCreateSerializer,
    ReturnCaseDetailSerializer,
    ReturnCaseStatusUpdateSerializer,
    RiskScoreSerializer,
)
from returns.models import ReturnCase, RiskScore
from returns.services.cases import (
    ReturnCaseWorkflowError,
    add_case_note,
    update_return_case_status,
)
from returns.services.queue import build_queue_queryset, get_queue_summary, parse_queue_filters


def _get_case_for_request(*, user, case_id: str) -> ReturnCase:
    """Fetch a case and enforce object-level access."""
    case = get_object_or_404(
        ReturnCase.objects.select_related("customer__user", "merchant__user"),
        pk=case_id,
    )
    if not user_can_access_case(user, case):
        raise PermissionDenied("You do not have access to this return case.")
    return case


class ReturnCaseCreateAPIView(APIView):
    """Create return cases through the canonical workflow service."""

    permission_classes = [IsAuthenticated, IsCustomerOrAdmin]

    def post(self, request, *args, **kwargs):
        """Create a return case for the authenticated customer."""
        serializer = ReturnCaseCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        case = serializer.save()
        response_serializer = ReturnCaseDetailSerializer(case, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ReturnCaseDetailAPIView(APIView):
    """Retrieve return case detail subject to role-based access checks."""

    permission_classes = [IsAuthenticated]

    def get(self, request, case_id: str, *args, **kwargs):
        """Return case detail for the current user when permitted."""
        case = _get_case_for_request(user=request.user, case_id=case_id)
        serializer = ReturnCaseDetailSerializer(case, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReturnCaseStatusAPIView(APIView):
    """Update case status for ops users."""

    permission_classes = [IsAuthenticated, IsOpsOrAdmin]

    def patch(self, request, case_id: str, *args, **kwargs):
        """Apply a validated status transition."""
        case = _get_case_for_request(user=request.user, case_id=case_id)
        serializer = ReturnCaseStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_case = update_return_case_status(
                actor=request.user,
                case=case,
                input_data=serializer.to_service_input(),
            )
        except ReturnCaseWorkflowError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ReturnCaseDetailSerializer(updated_case, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ReturnCaseNoteAPIView(APIView):
    """Create internal ops notes for a case."""

    permission_classes = [IsAuthenticated, IsOpsOrAdmin]

    def post(self, request, case_id: str, *args, **kwargs):
        """Add an internal note to the supplied case."""
        case = _get_case_for_request(user=request.user, case_id=case_id)
        serializer = CaseNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = add_case_note(actor=request.user, case=case, body=serializer.validated_data["body"])
        response_serializer = CaseNoteSerializer(note)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ReturnCaseRiskAPIView(APIView):
    """Expose persisted risk output to ops and admin users only."""

    permission_classes = [IsAuthenticated]

    def get(self, request, case_id: str, *args, **kwargs):
        """Return risk output when the actor is allowed to see it."""
        case = _get_case_for_request(user=request.user, case_id=case_id)
        if not (is_ops(request.user) or is_admin(request.user)):
            raise PermissionDenied("Only ops and admins can view risk output.")

        risk_score = RiskScore.objects.filter(case=case).first()
        if risk_score is None:
            raise NotFound("Risk score not available for this case.")

        serializer = RiskScoreSerializer(risk_score)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OpsQueueListAPIView(ListAPIView):
    """Expose the canonical ops queue as a paginated DRF endpoint."""

    serializer_class = OpsQueueItemSerializer
    permission_classes = [IsAuthenticated, IsOpsOrAdmin]
    pagination_class = ContractPageNumberPagination

    def get_queryset(self):
        """Return the filtered and ordered queue queryset."""
        self.queue_filters = parse_queue_filters(self.request.query_params)
        return build_queue_queryset(self.queue_filters)

    def list(self, request, *args, **kwargs):
        """Return paginated queue results with filters and summary metadata."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        payload = {
            "count": queryset.count(),
            "next": None,
            "previous": None,
            "results": [],
            "filters": {
                "status": self.queue_filters.status,
                "priority": self.queue_filters.priority,
                "risk_label": self.queue_filters.risk_label,
                "search": self.queue_filters.search,
                "page": self.queue_filters.page,
            },
            "summary": get_queue_summary(queryset),
        }

        if page is not None:
            paginated_response = self.get_paginated_response(
                self.get_serializer(page, many=True).data
            )
            payload.update(paginated_response.data)
            payload["filters"]["page"] = self.paginator.page.number
            return Response(payload, status=status.HTTP_200_OK)

        payload["results"] = self.get_serializer(queryset, many=True).data
        return Response(payload, status=status.HTTP_200_OK)
