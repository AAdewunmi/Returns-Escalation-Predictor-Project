# path: tests/test_console_shell.py
"""Integration tests for ReturnHub console shell pages."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from tests.factories import (
    CaseEventFactory,
    CustomerProfileFactory,
    EvidenceDocumentFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    RiskScoreFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_ops_console_renders_for_ops_user(client) -> None:
    """Ops users should see the ops console shell."""
    ops_user = UserFactory(email="console-ops@example.com")
    add_group(ops_user, "Ops")
    ReturnCaseFactory.create_batch(2, status="submitted")

    client.force_login(ops_user)
    response = client.get("/console/ops/")

    assert response.status_code == 200
    assert "Ops Console" in response.content.decode()
    assert 'aria-label="Primary"' in response.content.decode()


@pytest.mark.django_db
def test_ops_route_renders_standalone_queue_page_for_ops_user(client) -> None:
    """Ops users should see the standalone /ops/ queue page."""

    ops_user = UserFactory(email="ops-route@example.com")
    add_group(ops_user, "Ops")
    ReturnCaseFactory.create_batch(2, status="submitted")

    client.force_login(ops_user)
    response = client.get("/ops/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Ops Queue" in body
    assert "Ops workspace" in body
    assert "Returns queue" in body
    assert 'id="ops-queue-table"' in body


@pytest.mark.django_db
def test_ops_route_returns_queue_table_partial_for_htmx_request(client) -> None:
    """HTMX requests to /ops/ should return only the queue table partial."""

    ops_user = UserFactory(email="ops-htmx@example.com")
    add_group(ops_user, "Ops")
    ReturnCaseFactory(order_reference="OPS-HTMX-1", status="submitted")

    client.force_login(ops_user)
    response = client.get("/ops/", HTTP_HX_REQUEST="true")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Return cases" in body
    assert "OPS-HTMX-1" in body
    assert "Ops workspace" not in body


@pytest.mark.django_db
def test_ops_case_detail_route_renders_standalone_ops_workspace(client) -> None:
    """Ops users should be able to open a case detail page from the standalone ops route."""

    ops_user = UserFactory(email="ops-case-detail@example.com")
    add_group(ops_user, "Ops")
    return_case = ReturnCaseFactory(order_reference="OPS-DETAIL-1")
    EvidenceDocumentFactory(return_case=return_case)
    CaseEventFactory(return_case=return_case, event_type="document_uploaded", actor=ops_user)
    RiskScoreFactory(case=return_case, label="high")

    client.force_login(ops_user)
    response = client.get(f"/ops/{return_case.pk}/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Ops Case Detail" in body
    assert "OPS-DETAIL-1" in body
    assert "Back to ops queue" in body
    assert 'id="case-upload-form"' in body
    assert "Document actions" in body


@pytest.mark.django_db
def test_customer_gets_403_on_ops_console(client) -> None:
    """Customers must not access the ops console."""
    customer_user = UserFactory(email="console-customer@example.com")
    add_group(customer_user, "Customer")
    CustomerProfileFactory(user=customer_user)

    client.force_login(customer_user)
    response = client.get("/console/ops/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_gets_403_on_ops_case_detail_route(client) -> None:
    """Customers must not access the standalone ops case detail route."""

    customer_user = UserFactory(email="ops-detail-customer@example.com")
    add_group(customer_user, "Customer")
    return_case = ReturnCaseFactory()

    client.force_login(customer_user)
    response = client.get(f"/ops/{return_case.pk}/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_console_shows_customer_shell(client) -> None:
    """Customers should be able to load their own console shell."""
    customer_user = UserFactory(email="console-customer-own@example.com")
    add_group(customer_user, "Customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    ReturnCaseFactory(customer=customer_profile)

    client.force_login(customer_user)
    response = client.get("/console/customer/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Customer Console" in body
    assert "See your own cases" in body


@pytest.mark.django_db
def test_merchant_console_renders_for_merchant_user(client) -> None:
    """Merchants should see the merchant console shell."""
    merchant_user = UserFactory(email="console-merchant@example.com")
    add_group(merchant_user, "Merchant")
    merchant_profile = MerchantProfileFactory(user=merchant_user)
    ReturnCaseFactory(merchant=merchant_profile)

    client.force_login(merchant_user)
    response = client.get("/console/merchant/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Merchant Console" in body
    assert "Review linked cases" in body


@pytest.mark.django_db
def test_authenticated_console_nav_uses_post_logout_form(client) -> None:
    """The shared console nav should submit logout via POST instead of a GET link."""
    ops_user = UserFactory(email="console-logout@example.com")
    add_group(ops_user, "Ops")

    client.force_login(ops_user)
    response = client.get("/console/ops/")

    body = response.content.decode()
    assert response.status_code == 200
    assert 'method="post"' in body
    assert 'action="/logout/"' in body
    assert "Sign out" in body


@pytest.mark.django_db
def test_admin_console_does_not_render_return_to_landing_button(client) -> None:
    """The admin dashboard should not show a landing-page return action."""
    admin_user = UserFactory(email="console-admin@example.com", is_superuser=True, is_staff=True)
    add_group(admin_user, "Admin")

    client.force_login(admin_user)
    response = client.get("/console/admin/")

    body = response.content.decode()
    assert response.status_code == 200
    assert "Return to landing page" not in body
