"""Tests for the shared pagination contract."""

from django.core.paginator import InvalidPage, Page, Paginator
from django.template.loader import render_to_string
from django.test import RequestFactory
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from common.pagination import paginate_queryset
from core.api.pagination import ContractPageNumberPagination
from returns.models import ReturnCase
from tests.factories import ReturnCaseFactory


def test_paginate_queryset_defaults_to_first_page_for_missing_or_invalid_values(db) -> None:
    """Missing, non-integer, and non-positive values should resolve to page one."""
    ReturnCaseFactory.create_batch(31)

    queryset = ReturnCase.objects.order_by("id")

    assert paginate_queryset(queryset, None).page_obj.number == 1
    assert paginate_queryset(queryset, "banana").page_obj.number == 1
    assert paginate_queryset(queryset, "0").page_obj.number == 1
    assert paginate_queryset(queryset, "-2").page_obj.number == 1


def test_paginate_queryset_returns_last_page_when_out_of_range(db) -> None:
    """Out-of-range page numbers should resolve to the last page."""
    ReturnCaseFactory.create_batch(31)

    queryset = ReturnCase.objects.order_by("id")
    pagination = paginate_queryset(queryset, "999")

    assert pagination.page_obj.number == 3
    assert list(pagination.page_obj.object_list.values_list("order_reference", flat=True))[
        -1
    ].startswith("TEST-")


def test_pagination_partial_preserves_active_filters(db) -> None:
    """Pagination links should preserve the active filter query string."""
    ReturnCaseFactory.create_batch(31)
    queryset = ReturnCase.objects.order_by("id")
    pagination = paginate_queryset(queryset, "2")
    request = RequestFactory().get(
        "/ops/",
        {"status": "submitted", "search": "damaged", "page": "2"},
    )

    rendered = render_to_string(
        "partials/_pagination.html",
        {
            "request": request,
            "pagination": pagination,
        },
    )

    assert "Showing 16-30 of 31" in rendered
    assert "status=submitted" in rendered
    assert "search=damaged" in rendered
    assert "page=1" in rendered
    assert "page=3" in rendered


def test_contract_api_pagination_handles_empty_querysets(db) -> None:
    """Empty querysets should resolve safely to page one with no results."""
    request = Request(APIRequestFactory().get("/api/returns/queue/"))
    pagination = ContractPageNumberPagination()

    page = pagination.paginate_queryset(ReturnCase.objects.none(), request)
    response = pagination.get_paginated_response(page)

    assert page == []
    assert pagination.page.number == 1
    assert response.data["count"] == 0
    assert response.data["results"] == []


def test_contract_api_pagination_falls_back_to_first_page_on_invalid_paginator_page(db) -> None:
    """Paginator page errors should return the first page rather than raising."""

    class FlakyPaginator(Paginator):
        """Raise an invalid-page error once to exercise the defensive fallback."""

        def __init__(self, object_list, per_page, *args, **kwargs):
            super().__init__(object_list, per_page, *args, **kwargs)
            self._first_call = True

        def page(self, number) -> Page:
            if self._first_call:
                self._first_call = False
                raise InvalidPage("simulated invalid page")
            return super().page(number)

    ReturnCaseFactory.create_batch(5)
    request = Request(APIRequestFactory().get("/api/returns/queue/", {"page": "1"}))
    pagination = ContractPageNumberPagination()
    pagination.django_paginator_class = FlakyPaginator

    page = pagination.paginate_queryset(ReturnCase.objects.order_by("id"), request)

    assert len(page) == 5
    assert pagination.page.number == 1
