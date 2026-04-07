# path: returns/test_ops_case_detail.py
"""Integration tests for the ops case detail page."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.returns.models import CaseEvent
from tests.factories.accounts import UserFactory
from tests.factories.returns import (
    CustomerProfileFactory,
    EvidenceDocumentFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    RiskScoreFactory,
)


def _add_group(user, name: str) -> None:
    """Attach a user to a named Django group."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db()
def test_ops_case_detail_renders_evidence_timeline_and_risk(client):
    """Ops users should be able to inspect the full case detail page."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    case = ReturnCaseFactory()
    EvidenceDocumentFactory(case=case, original_filename="photo-proof.jpg")
    RiskScoreFactory(case=case, label="high", score="0.82", reason_codes=["long_message", "high_value_order"])
    CaseEvent.objects.create(case=case, event_type="case_created")

    response = client.get(reverse("ops:case-detail", args=[case.pk]))

    content = response.content.decode()

    assert response.status_code == 200
    assert case.reference in content
    assert "photo-proof.jpg" in content
    assert "Escalation risk" in content
    assert "Audit timeline" in content


@pytest.mark.django_db()
def test_ops_case_detail_blocks_authenticated_wrong_role(client):
    """Authenticated non-ops users should receive a clean 403 page."""
    customer_user = UserFactory()
    _add_group(customer_user, "customer")
    client.force_login(customer_user)

    case = ReturnCaseFactory()

    response = client.get(reverse("ops:case-detail", args=[case.pk]))

    assert response.status_code == 403
    assert "Forbidden" in response.content.decode()


@pytest.mark.django_db()
def test_ops_case_detail_returns_404_for_missing_case(client):
    """Unknown case identifiers should return a 404 response."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    response = client.get(reverse("ops:case-detail", args=["missing-case-id"]))

    assert response.status_code == 404


@pytest.mark.django_db()
def test_ops_case_detail_shows_empty_states_when_case_is_sparse(client):
    """The page should remain readable when evidence and risk are absent."""
    ops_user = UserFactory()
    _add_group(ops_user, "ops")
    client.force_login(ops_user)

    customer = CustomerProfileFactory()
    merchant = MerchantProfileFactory()
    case = ReturnCaseFactory(customer=customer, merchant=merchant)

    response = client.get(reverse("ops:case-detail", args=[case.pk]))

    content = response.content.decode()

    assert response.status_code == 200
    assert "No evidence yet" in content
    assert "No risk score yet" in content
