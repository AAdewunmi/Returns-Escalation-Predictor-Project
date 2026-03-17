"""Tests for the return-case workflow service."""

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from returns.models import CaseEvent, ReturnCase
from returns.services.cases import (
    ReturnCaseCreateInput,
    ReturnCaseWorkflowError,
    StatusUpdateInput,
    _actor_role,
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


def _add_group(user, name: str) -> None:
    """Attach a named group to the supplied user."""
    group, _ = Group.objects.get_or_create(name=name)
    user.groups.add(group)


@pytest.mark.django_db
def test_create_return_case_persists_case_and_event() -> None:
    """Creating a case should persist normalized data and an audit event."""
    customer_profile = CustomerProfileFactory()
    merchant_profile = MerchantProfileFactory()
    _add_group(customer_profile.user, "Customer")

    case = create_return_case(
        actor=customer_profile.user,
        input_data=ReturnCaseCreateInput(
            merchant_profile=merchant_profile,
            external_order_ref="  ORD-1001  ",
            item_category=" Apparel ",
            return_reason=" Damaged Item ",
            customer_message="  Box arrived open.  ",
            order_value=Decimal("59.99"),
            delivery_date=datetime.date(2025, 1, 10),
        ),
    )

    assert case.customer == customer_profile
    assert case.merchant == merchant_profile
    assert case.order_reference == "ORD-1001"
    assert case.item_category == "apparel"
    assert case.return_reason == "damaged item"
    assert case.customer_message == "Box arrived open."
    assert case.status == ReturnCase.Status.SUBMITTED
    assert case.priority == ReturnCase.Priority.MEDIUM
    assert case.last_status_changed_at is not None

    event = CaseEvent.objects.get(return_case=case, event_type="case_created")
    assert event.actor == customer_profile.user
    assert event.actor_role == "customer"
    assert event.payload["order_reference"] == "ORD-1001"


@pytest.mark.django_db
def test_create_return_case_rejects_non_customer_actor() -> None:
    """Only customers and admins should be allowed to create cases."""
    actor = UserFactory()
    merchant_profile = MerchantProfileFactory()

    with pytest.raises(PermissionDenied):
        create_return_case(
            actor=actor,
            input_data=ReturnCaseCreateInput(
                merchant_profile=merchant_profile,
                external_order_ref="ORD-1002",
                item_category="apparel",
                return_reason="damaged",
                customer_message="Need help",
                order_value=Decimal("10.00"),
                delivery_date=datetime.date(2025, 1, 11),
            ),
        )


@pytest.mark.django_db
def test_create_return_case_rejects_customer_without_profile() -> None:
    """A customer-group actor still needs an attached customer profile."""
    actor = UserFactory()
    merchant_profile = MerchantProfileFactory()
    _add_group(actor, "Customer")

    with pytest.raises(ReturnCaseWorkflowError):
        create_return_case(
            actor=actor,
            input_data=ReturnCaseCreateInput(
                merchant_profile=merchant_profile,
                external_order_ref="ORD-1003",
                item_category="apparel",
                return_reason="damaged",
                customer_message="Need help",
                order_value=Decimal("10.00"),
                delivery_date=datetime.date(2025, 1, 12),
            ),
        )


@pytest.mark.django_db
def test_update_return_case_status_updates_case_and_emits_event() -> None:
    """Ops should be able to move a case through allowed transitions."""
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED)

    updated_case = update_return_case_status(
        actor=ops_user,
        case=case,
        input_data=StatusUpdateInput(
            status=ReturnCase.Status.IN_REVIEW,
            priority=ReturnCase.Priority.HIGH,
        ),
    )

    updated_case.refresh_from_db()

    assert updated_case.status == ReturnCase.Status.IN_REVIEW
    assert updated_case.priority == ReturnCase.Priority.HIGH
    assert updated_case.last_status_changed_at is not None

    event = CaseEvent.objects.get(return_case=case, event_type="status_updated")
    assert event.actor == ops_user
    assert event.actor_role == "ops"
    assert event.payload["previous_status"] == ReturnCase.Status.SUBMITTED
    assert event.payload["new_status"] == ReturnCase.Status.IN_REVIEW


@pytest.mark.django_db
def test_update_return_case_status_keeps_existing_priority_when_none_supplied() -> None:
    """Status updates should not rewrite priority when none is provided."""
    admin_user = UserFactory(is_superuser=True)
    case = ReturnCaseFactory(
        status=ReturnCase.Status.WAITING_CUSTOMER,
        priority=ReturnCase.Priority.HIGH,
    )

    updated_case = update_return_case_status(
        actor=admin_user,
        case=case,
        input_data=StatusUpdateInput(status=ReturnCase.Status.APPROVED),
    )

    updated_case.refresh_from_db()

    assert updated_case.status == ReturnCase.Status.APPROVED
    assert updated_case.priority == ReturnCase.Priority.HIGH

    event = CaseEvent.objects.get(return_case=case, event_type="status_updated")
    assert event.actor_role == "admin"
    assert event.payload["previous_priority"] == ReturnCase.Priority.HIGH
    assert event.payload["new_priority"] == ReturnCase.Priority.HIGH


@pytest.mark.django_db
def test_update_return_case_status_rejects_invalid_transition() -> None:
    """Invalid state changes should raise a workflow error."""
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory(status=ReturnCase.Status.APPROVED)

    with pytest.raises(ReturnCaseWorkflowError):
        update_return_case_status(
            actor=ops_user,
            case=case,
            input_data=StatusUpdateInput(status=ReturnCase.Status.IN_REVIEW),
        )


@pytest.mark.django_db
def test_update_return_case_status_rejects_non_ops_actor() -> None:
    """Status changes are restricted to ops/admin actors."""
    actor = UserFactory()
    case = ReturnCaseFactory(status=ReturnCase.Status.SUBMITTED)

    with pytest.raises(PermissionDenied):
        update_return_case_status(
            actor=actor,
            case=case,
            input_data=StatusUpdateInput(status=ReturnCase.Status.IN_REVIEW),
        )


@pytest.mark.django_db
def test_add_case_note_persists_internal_note_and_event() -> None:
    """Adding a note should create both the note and its audit event."""
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory()

    note = add_case_note(actor=ops_user, case=case, body="  Followed up with merchant.  ")

    assert note.return_case == case
    assert note.author == ops_user
    assert note.body == "Followed up with merchant."
    assert note.is_internal is True

    event = CaseEvent.objects.get(return_case=case, event_type="note_added")
    assert event.actor == ops_user
    assert event.payload["note_id"] == str(note.pk)


@pytest.mark.django_db
def test_add_case_note_rejects_non_ops_actor() -> None:
    """Notes are restricted to ops/admin actors."""
    actor = UserFactory()
    case = ReturnCaseFactory()

    with pytest.raises(PermissionDenied):
        add_case_note(actor=actor, case=case, body="Need review")


@pytest.mark.django_db
def test_add_case_note_rejects_blank_body() -> None:
    """Blank notes should be rejected before persistence."""
    ops_user = UserFactory()
    _add_group(ops_user, "Ops")
    case = ReturnCaseFactory()

    with pytest.raises(ReturnCaseWorkflowError):
        add_case_note(actor=ops_user, case=case, body="   ")


@pytest.mark.django_db
def test_actor_role_returns_expected_labels() -> None:
    """Actor-role helper should map seeded role groups consistently."""
    merchant_profile = MerchantProfileFactory()
    _add_group(merchant_profile.user, "Merchant")

    customer_profile = CustomerProfileFactory()
    _add_group(customer_profile.user, "Customer")

    anonymous_actor = UserFactory()
    admin_user = UserFactory(is_superuser=True)

    assert _actor_role(admin_user) == "admin"
    assert _actor_role(merchant_profile.user) == "merchant"
    assert _actor_role(customer_profile.user) == "customer"
    assert _actor_role(anonymous_actor) == ""
