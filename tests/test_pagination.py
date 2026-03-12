"""Tests for shared pagination helpers."""

from common.pagination import (
    DEFAULT_PAGE_SIZE,
    build_page_numbers,
    normalise_page_number,
    paginate_queryset,
)


def test_normalise_page_number_handles_missing_invalid_and_non_positive_values():
    """Invalid page inputs should normalize to the first page."""
    assert normalise_page_number(None) == 1
    assert normalise_page_number("abc") == 1
    assert normalise_page_number("0") == 1
    assert normalise_page_number("-5") == 1


def test_normalise_page_number_accepts_positive_integer_text():
    """Positive integer text should be preserved."""
    assert normalise_page_number("3") == 3


def test_build_page_numbers_returns_window_around_current_page():
    """Window should include pages around the active page within bounds."""
    context = paginate_queryset(list(range(1, 101)), raw_page="4")

    assert build_page_numbers(context.page_obj) == [2, 3, 4, 5, 6]


def test_build_page_numbers_clamps_at_start_and_end():
    """Window should clamp near boundaries."""
    first_context = paginate_queryset(list(range(1, 101)), raw_page="1")
    last_context = paginate_queryset(list(range(1, 101)), raw_page="7")

    assert build_page_numbers(first_context.page_obj) == [1, 2, 3]
    assert build_page_numbers(last_context.page_obj) == [5, 6, 7]


def test_paginate_queryset_uses_default_page_size_and_count_line_for_non_empty_results():
    """Pagination context should reflect standard page sizing and count text."""
    context = paginate_queryset(list(range(1, 101)), raw_page="2")

    assert context.page_obj.number == 2
    assert context.page_obj.paginator.per_page == DEFAULT_PAGE_SIZE
    assert context.count_line == "Showing 16-30 of 100"


def test_paginate_queryset_handles_out_of_range_by_falling_back_to_last_page():
    """Out-of-range page requests should return the final page."""
    context = paginate_queryset(list(range(1, 101)), raw_page="999")

    assert context.page_obj.number == 7
    assert context.count_line == "Showing 91-100 of 100"


def test_paginate_queryset_handles_empty_collections():
    """Empty querysets/lists should keep page 1 and zero count line."""
    context = paginate_queryset([], raw_page="5")

    assert context.page_obj.number == 1
    assert context.count_line == "Showing 0-0 of 0"
