# path: tests/test_ops_queue_api.py
"""Integration tests for the ops queue API."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.test import APIClient

from returns.api.views import OpsQueueListAPIView
from returns.models import RiskScore
from tests.factories import ReturnCaseFactory, UserFactory


def _ops_user():
    """Create and return an ops-authenticated user."""

    user = UserFactory()
    ops_group, _ = Group.objects.get_or_create(name="ops")
    user.groups.add(ops_group)
    return user


def _queue_url() -> str:
    """Return the namespaced URL for the ops queue API."""

    return reverse("returns-api:ops-queue-api")


@pytest.mark.django_db
def test_ops_queue_api_returns_paginated_results_with_summary() -> None:
    """The queue API should paginate at 15 and return summary metadata."""

    for index in range(18):
        case = ReturnCaseFactory(order_reference=f"ORD-{1000 + index}")
        RiskScore.objects.create(
            case=case,
            model_version="baseline-v1",
            score="0.32",
            label="medium",
            reason_codes=["CUSTOMER_MESSAGE_LONG"],
            scored_at=case.created_at,
        )

    client = APIClient()
    client.force_authenticate(user=_ops_user())

    response = client.get(_queue_url(), {"page": 2})

    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 18
    assert len(payload["results"]) == 3
    assert payload["summary"]["total"] == 18
    assert payload["filters"]["page"] == 2
    assert payload["previous"] is not None


@pytest.mark.django_db
def test_ops_queue_api_invalid_and_out_of_range_pages_follow_contract() -> None:
    """Invalid page inputs should fall back safely rather than returning an error."""

    for index in range(17):
        ReturnCaseFactory(order_reference=f"ORD-{2000 + index}")

    client = APIClient()
    client.force_authenticate(user=_ops_user())

    invalid_response = client.get(_queue_url(), {"page": "banana"})
    out_of_range_response = client.get(_queue_url(), {"page": 999})

    assert invalid_response.status_code == 200
    assert len(invalid_response.json()["results"]) == 15
    assert invalid_response.json()["filters"]["page"] == 1

    assert out_of_range_response.status_code == 200
    assert len(out_of_range_response.json()["results"]) == 2
    assert out_of_range_response.json()["filters"]["page"] == 2


@pytest.mark.django_db
def test_ops_queue_api_rejects_wrong_role() -> None:
    """Non-ops users should not be able to access the queue API."""

    client = APIClient()
    client.force_authenticate(user=UserFactory())

    response = client.get(_queue_url())

    assert response.status_code == 403


@pytest.mark.django_db
def test_ops_queue_api_applies_filters_before_pagination() -> None:
    """Risk and status filters should narrow the result set before pagination occurs."""

    matching_case = ReturnCaseFactory(status="submitted")
    ignored_case = ReturnCaseFactory(status="approved")

    RiskScore.objects.create(
        case=matching_case,
        model_version="baseline-v1",
        score="0.83",
        label="high",
        reason_codes=["PRIOR_RETURNS_HIGH"],
        scored_at=matching_case.created_at,
    )
    RiskScore.objects.create(
        case=ignored_case,
        model_version="baseline-v1",
        score="0.20",
        label="low",
        reason_codes=["BASELINE_PATTERN_LOW_SIGNAL"],
        scored_at=ignored_case.created_at,
    )

    client = APIClient()
    client.force_authenticate(user=_ops_user())

    response = client.get(
        _queue_url(),
        {"status": "submitted", "risk_label": "high"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 1
    assert payload["results"][0]["id"] == matching_case.id


@pytest.mark.django_db
def test_ops_queue_api_view_returns_unpaginated_payload_when_pagination_is_skipped() -> None:
    """The list view should still return filters and results when pagination is bypassed."""
    case = ReturnCaseFactory(order_reference="OPS-FALLBACK-1")
    view = OpsQueueListAPIView()
    request = Request(APIRequestFactory().get(_queue_url(), {"status": "submitted"}))
    request.user = _ops_user()
    view.request = request
    view.args = ()
    view.kwargs = {}

    def fake_paginate_queryset(queryset):
        return None

    def fake_get_serializer(queryset, many=False):
        class StubSerializer:
            data = [{"id": case.id, "order_reference": case.order_reference}]

        return StubSerializer()

    view.paginate_queryset = fake_paginate_queryset
    view.get_serializer = fake_get_serializer

    response = view.list(request)

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["filters"]["status"] == "submitted"
    assert response.data["results"] == [{"id": case.id, "order_reference": case.order_reference}]
