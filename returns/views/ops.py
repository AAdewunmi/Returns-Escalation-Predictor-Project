# path: returns/views/ops.py
"""Views for the ops queue surface."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.returns.services.ops_queue import build_ops_queue_context, parse_ops_queue_filters


def _user_can_access_ops(user) -> bool:
    """Return True when the current user can access the ops surface."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name="ops").exists()


@login_required(login_url="/login/ops/")
def ops_queue(request: HttpRequest) -> HttpResponse:
    """Render the ops queue page and HTMX queue table updates."""
    if not _user_can_access_ops(request.user):
        return render(request, "errors/403.html", status=403)

    filters = parse_ops_queue_filters(request.GET)
    context = build_ops_queue_context(filters, request.GET.get("page"))
    context["status_options"] = [
        ("submitted", "Submitted"),
        ("in_review", "In review"),
        ("awaiting_customer", "Awaiting customer"),
        ("awaiting_merchant", "Awaiting merchant"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("closed", "Closed"),
    ]
    context["priority_options"] = [
        ("high", "High"),
        ("normal", "Normal"),
        ("low", "Low"),
    ]

    if request.headers.get("HX-Request") == "true":
        return render(request, "ops/partials/_queue_table.html", context)

    return render(request, "ops/queue.html", context)
