# path: tests/test_forbidden_template.py
"""Integration tests for shared forbidden page rendering."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.accounts.constants import GROUP_NAMES, ROLE_CUSTOMER

pytestmark = pytest.mark.django_db


def test_wrong_role_renders_shared_403_page(client, django_user_model):
    """Authenticated wrong-role access should render the shared forbidden template."""
    group, _ = Group.objects.get_or_create(name=GROUP_NAMES[ROLE_CUSTOMER])
    user = django_user_model.objects.create_user("customer.nav", "customer.nav@example.com", "pass-12345")
    user.groups.add(group)

    client.force_login(user)
    response = client.get(reverse("accounts:console_ops"))

    assert response.status_code == 403
    assert b"You do not have access to this surface" in response.content
    assert b"Customer portal" in response.content
