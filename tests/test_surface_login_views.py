# path: tests/test_surface_login_views.py
"""Integration tests for surface login routing."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import GROUP_NAMES, ROLE_CUSTOMER, ROLE_OPS

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


def test_customer_login_redirects_to_customer_console(client):
    """Customer login should land on the customer console."""
    user = create_user_for_role("customer.one", ROLE_CUSTOMER)

    response = client.post(
        reverse("accounts:login_customer"),
        {"username": user.username, "password": "pass-12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:console_customer")


def test_wrong_surface_login_redirects_to_primary_surface(client):
    """An ops user using the customer login page should be routed to the ops console."""
    user = create_user_for_role("ops.one", ROLE_OPS)

    response = client.post(
        reverse("accounts:login_customer"),
        {"username": user.username, "password": "pass-12345"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:console_ops")


def test_surface_login_preserves_allowed_next_path(client):
    """A surface login should honour an allowed next path for the same user role."""
    user = create_user_for_role("customer.two", ROLE_CUSTOMER)
    target_path = "/console/customer/"

    response = client.post(
        f"{reverse('accounts:login_customer')}?next={target_path}",
        {"username": user.username, "password": "pass-12345", "next": target_path},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == target_path
