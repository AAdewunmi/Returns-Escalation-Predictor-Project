# path: tests/test_console_access.py
"""Integration tests for surface console access behaviour."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from accounts.constants import GROUP_NAMES, ROLE_CUSTOMER, ROLE_OPS

pytestmark = pytest.mark.django_db

User = get_user_model()


def create_user_for_role(username, role, password="pass-12345"):
    """Create a user assigned to the requested role group."""
    group, _ = Group.objects.get_or_create(name=GROUP_NAMES[role])
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=password,
    )
    user.groups.add(group)
    return user


def test_anonymous_customer_console_redirects_to_customer_login(client):
    """Anonymous users should be sent to the customer login page with next preserved."""
    response = client.get(reverse("accounts:console_customer"))

    assert response.status_code == 302
    assert response.headers["Location"].startswith(reverse("accounts:login_customer"))
    assert "next=/console/customer/" in response.headers["Location"]


def test_customer_can_access_customer_console(client):
    """Customers may open their own console."""
    user = create_user_for_role("customer.one", ROLE_CUSTOMER)
    client.force_login(user)

    response = client.get(reverse("accounts:console_customer"))

    assert response.status_code == 200
    assert b"Track the most recent return activity in one customer-facing shell." in response.content


def test_customer_gets_403_on_ops_console(client):
    """Authenticated wrong-role users should receive a clean 403 response."""
    user = create_user_for_role("customer.two", ROLE_CUSTOMER)
    client.force_login(user)

    response = client.get(reverse("accounts:console_ops"))

    assert response.status_code == 403


def test_ops_can_access_ops_console(client):
    """Ops users may open their own console."""
    user = create_user_for_role("ops.one", ROLE_OPS)
    client.force_login(user)

    response = client.get(reverse("accounts:console_ops"))

    assert response.status_code == 200
    assert b"Work the live return queue inside the same shared ReturnHub shell." in response.content
