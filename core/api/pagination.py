# path: core/api/pagination.py
"""Shared API pagination primitives for ReturnHub."""

from __future__ import annotations

from django.core.paginator import EmptyPage, InvalidPage, Paginator
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ContractPageNumberPagination(PageNumberPagination):
    """
    Page-number pagination that follows the explicit ReturnHub contract.

    Invalid values fall back to page 1, and out-of-range pages fall back to
    the last available page rather than returning a 404-style error payload.
    """

    page_size = 15
    page_query_param = "page"
    page_size_query_param = None
    django_paginator_class = Paginator

    def paginate_queryset(self, queryset, request, view=None):  # type: ignore[override]
        """Paginate a queryset using contract-safe page handling."""

        self.request = request
        paginator = self.django_paginator_class(queryset, self.page_size)

        raw_page = request.query_params.get(self.page_query_param, "1")
        try:
            page_number = int(raw_page)
        except (TypeError, ValueError):
            page_number = 1

        if page_number <= 0:
            page_number = 1

        if paginator.count == 0:
            page_number = 1
        elif page_number > paginator.num_pages:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except (EmptyPage, InvalidPage):
            self.page = paginator.page(1)

        self.display_page_controls = paginator.num_pages > 1
        return list(self.page)

    def get_paginated_response(self, data):  # type: ignore[override]
        """Return the standard paginated response shape."""

        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )
