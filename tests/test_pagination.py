"""Tests for the shared pagination contract."""

from django.template.loader import render_to_string
from django.test import RequestFactory

from common.pagination import paginate_queryset
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
