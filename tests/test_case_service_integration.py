# path: tests/test_case_service_integration.py
"""DB-hitting integration tests for the ReturnHub case workflow service."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from returns.models import CaseEvent, CaseNote, ReturnCase
from returns.services.cases import (
    ReturnCaseCreateInput,
    add_case_note,
    create_return_case,
)
from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_create_return_case_persists_customer_supplied_fields() -> None:
    """The workflow service should persist customer input and audit state."""
    customer_user = UserFactory(email="integration-customer@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)
    merchant_profile = MerchantProfileFactory()

    created_case = create_return_case(
        actor=customer_user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant_profile,
            external_order_ref="ORDER-2048",
            item_category="apparel",
            return_reason="wrong_size",
            customer_message="The item is labelled medium but fits like extra small.",
            order_value=Decimal("89.50"),
            delivery_date=merchant_profile.created_at.date(),
        ),
    )

    persisted_case = ReturnCase.objects.get(pk=created_case.pk)

    assert persisted_case.order_reference == "ORDER-2048"
    assert persisted_case.item_category == "apparel"
    assert persisted_case.return_reason == "wrong_size"
    assert CaseEvent.objects.filter(return_case=persisted_case, event_type="case_created").exists()


@pytest.mark.django_db
def test_add_case_note_appends_note_and_case_event() -> None:
    """Adding a note should create both a CaseNote row and matching audit event."""
    ops_user = UserFactory(email="integration-ops@example.com")
    add_group(ops_user, "ops")
    case = ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW)

    note = add_case_note(
        actor=ops_user,
        case=case,
        body="Customer photo evidence looks consistent with transit damage.",
    )

    assert CaseNote.objects.filter(pk=note.pk, return_case=case).exists()
    assert CaseEvent.objects.filter(return_case=case, event_type="note_added").count() == 1
