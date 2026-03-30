# path: core/views/console.py
"""Role-specific console views for ReturnHub."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render

from apps.returns.services.queue import (
    QUEUE_PAGE_SIZE,
    build_filter_querystring,
    build_queue_queryset,
    get_queue_summary,
    parse_queue_filters,
)


def _user_has_ops_access(user) -> bool:
    """Return whether the user can access the ops console."""

    return user.is_superuser or user.groups.filter(name="ops").exists()


def _build_page_window(
    *,
    current_page: int,
    total_pages: int,
    radius: int = 2,
) -> list[int]:
    """Return a small page window around the current page."""

    if total_pages <= 0:
        return []

    start = max(1, current_page - radius)
    end = min(total_pages, current_page + radius)
    return list(range(start, end + 1))


@login_required
def ops_console(request):
    """Render the ops console queue preview."""

    if not _user_has_ops_access(request.user):
        raise PermissionDenied

    queue_filters = parse_queue_filters(request.GET)
    queryset = build_queue_queryset(queue_filters)

    paginator = Paginator(queryset, QUEUE_PAGE_SIZE)
    page_number = queue_filters.page

    if paginator.count == 0:
        page_number = 1
    elif page_number > paginator.num_pages:
        page_number = paginator.num_pages

    page_obj = paginator.get_page(page_number)
    start_index = page_obj.start_index() if paginator.count else 0
    end_index = page_obj.end_index() if paginator.count else 0

    context = {
        "queue_filters": queue_filters,
        "queue_summary": get_queue_summary(queryset),
        "page_obj": page_obj,
        "page_window": _build_page_window(
            current_page=page_obj.number,
            total_pages=paginator.num_pages,
        ),
        "filter_querystring": build_filter_querystring(request.GET),
        "total_count": paginator.count,
        "count_line": f"Showing {start_index}-{end_index} of {paginator.count}",
    }
    return render(request, "console/ops_dashboard.html", context)
