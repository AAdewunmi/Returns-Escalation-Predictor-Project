"""Integration tests for shared forbidden page rendering."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from accounts.constants import GROUP_NAMES, ROLE_CUSTOMER

pytestmark = pytest.mark.django_db


def test_wrong_role_renders_shared_403_page(client, django_user_model):
    """Authenticated wrong-role access should render the shared forbidden template."""

    group, _ = Group.objects.get_or_create(name=GROUP_NAMES[ROLE_CUSTOMER])
    user = django_user_model.objects.create_user(
        "customer.nav",
        "customer.nav@example.com",
        "pass-12345",
    )
    user.groups.add(group)

    client.force_login(user)
    response = client.get(reverse("accounts:console_ops"))

    assert response.status_code == 403
    assert b"403 Forbidden" in response.content
    assert b"This surface is outside your current access level." in response.content
    assert b"Go to sign in" in response.content
