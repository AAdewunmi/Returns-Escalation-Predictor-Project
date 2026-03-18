# path: tests/test_cases.py
"""Unit-style service tests for ReturnHub case workflow."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from returns.models import CaseEvent, ReturnCase
from returns.services.cases import (
    ReturnCaseCreateInput,
    ReturnCaseWorkflowError,
    StatusUpdateInput,
    add_case_note,
    create_return_case,
    update_return_case_status,
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
def test_create_return_case_sets_defaults_and_emits_event() -> None:
    """Creating a case should persist defaults and a case_created event."""
    customer_user = UserFactory(email="customer@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    merchant_profile = MerchantProfileFactory()

    created_case = create_return_case(
        actor=customer_user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant_profile,
            external_order_ref="ORDER-1001",
            item_category="electronics",
            return_reason="damaged",
            customer_message="The box arrived crushed and the screen is cracked.",
            order_value=Decimal("249.99"),
            delivery_date=customer_profile.created_at.date(),
        ),
    )

    assert created_case.customer == customer_profile
    assert created_case.status == ReturnCase.Status.SUBMITTED
    assert created_case.priority == ReturnCase.Priority.MEDIUM
    assert (
        CaseEvent.objects.filter(return_case=created_case, event_type="case_created").count() == 1
    )


@pytest.mark.django_db
def test_update_return_case_status_rejects_invalid_transition() -> None:
    """Terminal states should reject additional transitions."""
    ops_user = UserFactory(email="ops@example.com")
    add_group(ops_user, "ops")
    case = ReturnCaseFactory(status="approved")

    with pytest.raises(ReturnCaseWorkflowError):
        update_return_case_status(
            actor=ops_user,
            case=case,
            input_data=StatusUpdateInput(status=ReturnCase.Status.IN_REVIEW),
        )


@pytest.mark.django_db
def test_add_case_note_requires_ops_or_admin() -> None:
    """Customers must not be able to create internal ops notes."""
    customer_user = UserFactory(email="customer-2@example.com")
    add_group(customer_user, "customer")
    CustomerProfileFactory(user=customer_user)
    case = ReturnCaseFactory()

    with pytest.raises(PermissionDenied):
        add_case_note(actor=customer_user, case=case, body="This should fail.")
