# path: apps/returns/api/views/queue.py
"""API views for the ops queue."""

from __future__ import annotations

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.api.pagination import ContractPageNumberPagination
from returns.api.permissions import IsOpsOrAdmin
from returns.api.serializers import OpsQueueItemSerializer
from returns.services.queue import build_queue_queryset, get_queue_summary, parse_queue_filters


class OpsQueueListApiView(ListAPIView):
    """Expose the canonical ops queue as a paginated DRF endpoint."""

    serializer_class = OpsQueueItemSerializer
    permission_classes = [IsAuthenticated, IsOpsOrAdmin]
    pagination_class = ContractPageNumberPagination

    def get_queryset(self):
        """Return the filtered and ordered queue queryset."""

        self.queue_filters = parse_queue_filters(self.request.query_params)
        return build_queue_queryset(self.queue_filters)

    def list(self, request, *args, **kwargs) -> Response:
        """Return the paginated queue payload with filter echoing and summary data."""

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
            payload["filters"]["page"] = self.page.number
            return Response(payload)

        payload["results"] = self.get_serializer(queryset, many=True).data
        return Response(payload)
