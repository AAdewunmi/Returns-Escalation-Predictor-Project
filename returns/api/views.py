# path: returns/api/views.py
"""DRF views for the ReturnHub return workflow."""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from returns.api.permissions import IsCustomerOrAdmin, IsOpsOrAdmin, user_can_access_case
from returns.api.serializers import (
    CaseNoteCreateSerializer,
    CaseNoteSerializer,
    ReturnCaseCreateSerializer,
    ReturnCaseDetailSerializer,
    ReturnCaseStatusUpdateSerializer,
)
from returns.models import ReturnCase
from returns.services.cases import (
    ReturnCaseWorkflowError,
    add_case_note,
    update_return_case_status,
)


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
