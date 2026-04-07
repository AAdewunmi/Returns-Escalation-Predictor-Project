"""Focused tests for the shared ops case detail service."""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied

from returns.services.ops_case_detail import (
    build_ops_case_detail_context,
    get_case_detail_actor_role,
)
from tests.factories import MerchantProfileFactory, ReturnCaseFactory, UserFactory


@pytest.mark.django_db
def test_get_case_detail_actor_role_returns_empty_for_unscoped_user() -> None:
    """Users outside the case roles should not receive a workspace actor role."""

    return_case = ReturnCaseFactory()
    actor = UserFactory()

    assert get_case_detail_actor_role(actor=actor, return_case=return_case) == ""


@pytest.mark.django_db
def test_get_case_detail_actor_role_returns_ops_for_ops_user() -> None:
    """Ops users should receive the ops workspace role immediately."""

    return_case = ReturnCaseFactory()
    actor = UserFactory()
    actor.groups.create(name="ops")

    assert get_case_detail_actor_role(actor=actor, return_case=return_case) == "ops"


@pytest.mark.django_db
def test_get_case_detail_actor_role_rejects_unlinked_customer() -> None:
    """Customers outside the case should be denied explicitly."""

    return_case = ReturnCaseFactory()
    actor = UserFactory()
    actor.groups.create(name="customer")

    with pytest.raises(PermissionDenied):
        get_case_detail_actor_role(actor=actor, return_case=return_case)


@pytest.mark.django_db
def test_get_case_detail_actor_role_returns_merchant_for_linked_merchant() -> None:
    """The linked merchant should receive the merchant workspace role."""

    merchant_profile = MerchantProfileFactory()
    return_case = ReturnCaseFactory(merchant=merchant_profile)
    actor = merchant_profile.user
    actor.groups.create(name="merchant")

    assert get_case_detail_actor_role(actor=actor, return_case=return_case) == "merchant"


@pytest.mark.django_db
def test_get_case_detail_actor_role_rejects_unlinked_merchant() -> None:
    """Merchants outside the case should be denied explicitly."""

    return_case = ReturnCaseFactory()
    actor = UserFactory()
    actor.groups.create(name="merchant")

    with pytest.raises(PermissionDenied):
        get_case_detail_actor_role(actor=actor, return_case=return_case)


@pytest.mark.django_db
def test_build_ops_case_detail_context_returns_empty_documents_on_permission_error(
    monkeypatch,
) -> None:
    """Document listing failures should degrade to an empty document queryset."""

    return_case = ReturnCaseFactory()
    actor = return_case.customer.user
    actor.groups.create(name="customer")
    monkeypatch.setattr(
        "returns.services.ops_case_detail.list_documents_for_case",
        lambda **kwargs: (_ for _ in ()).throw(PermissionDenied("forbidden")),
    )

    context = build_ops_case_detail_context(case_id=return_case.pk, actor=actor)

    assert list(context["documents"]) == []


@pytest.mark.django_db
def test_build_ops_case_detail_context_defaults_for_no_actor() -> None:
    """Anonymous or omitted actors should receive the base case context without a role."""

    return_case = ReturnCaseFactory(order_reference="OPS-SVC-001")

    context = build_ops_case_detail_context(case_id=return_case.pk)

    assert context["actor_role"] == ""
    assert context["page_title"] == "Case OPS-SVC-001"
