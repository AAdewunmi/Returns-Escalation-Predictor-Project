# path: common/pagination.py
"""Shared pagination helpers for fixed-size paginated list surfaces."""
from dataclasses import dataclass

from django.core.paginator import EmptyPage, Page, Paginator

DEFAULT_PAGE_SIZE = 15
DEFAULT_PAGE_WINDOW = 2


@dataclass(frozen=True)
class PaginationContext:
    """Pagination state consumed by views and the shared template partial."""

    page_obj: Page
    page_numbers: list[int]

    @property
    def count_line(self) -> str:
        """Return the standard visible count line."""
        if self.page_obj.paginator.count == 0:
            return "Showing 0-0 of 0"
        return (
            f"Showing {self.page_obj.start_index()}-"
            f"{self.page_obj.end_index()} of {self.page_obj.paginator.count}"
        )


def normalise_page_number(raw_page: str | None) -> int:
    """Normalise incoming page values to the first page when invalid."""
    if raw_page is None:
        return 1
    try:
        page_number = int(raw_page)
    except (TypeError, ValueError):
        return 1
    return page_number if page_number > 0 else 1


def build_page_numbers(page_obj: Page, radius: int = DEFAULT_PAGE_WINDOW) -> list[int]:
    """Build a compact page-number window around the current page."""
    start = max(page_obj.number - radius, 1)
    end = min(page_obj.number + radius, page_obj.paginator.num_pages)
    return list(range(start, end + 1))


def paginate_queryset(queryset, raw_page: str | None) -> PaginationContext:
    """Paginate a queryset using the fixed ReturnHub contract."""
    paginator = Paginator(queryset, DEFAULT_PAGE_SIZE)
    page_number = normalise_page_number(raw_page)

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return PaginationContext(
        page_obj=page_obj,
        page_numbers=build_page_numbers(page_obj),
    )
