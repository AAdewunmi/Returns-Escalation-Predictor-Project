# path: tests/test_demo_seed_pagination_contract.py
"""Integration tests for demo seed pagination guarantees across product surfaces."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from apps.returns.models import CustomerProfile, MerchantProfile, ReturnCase

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_creates_enough_cases_for_second_page_across_roles() -> None:
    """The seeded environment should support page one and page two on each list surface."""
    call_command("seed_demo")

    customer = CustomerProfile.objects.select_related("user").get(user__username="customer_demo")
    merchant = MerchantProfile.objects.select_related("user").get(user__username="merchant_demo")

    assert ReturnCase.objects.count() >= 30
    assert ReturnCase.objects.filter(customer=customer).count() >= 16
    assert ReturnCase.objects.filter(merchant=merchant).count() >= 16


@pytest.mark.django_db
def test_ops_surface_renders_page_one_and_page_two(client) -> None:
    """The ops list should render both page one and page two with seeded data."""
    call_command("seed_demo")
    ops_user = User.objects.get(username="ops_demo")

    client.force_login(ops_user)

    page_one = client.get(reverse("ops-case-list"), {"page": 1})
    page_two = client.get(reverse("ops-case-list"), {"page": 2})

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert "Showing" in page_two.content.decode()


@pytest.mark.django_db
def test_customer_and_merchant_surfaces_render_second_page(client) -> None:
    """Customer and merchant list pages should both render page two after demo seeding."""
    call_command("seed_demo")

    customer_user = User.objects.get(username="customer_demo")
    merchant_user = User.objects.get(username="merchant_demo")

    client.force_login(customer_user)
    customer_page_two = client.get(reverse("customer-case-list"), {"page": 2})
    assert customer_page_two.status_code == 200

    client.logout()

    client.force_login(merchant_user)
    merchant_page_two = client.get(reverse("merchant-case-list"), {"page": 2})
    assert merchant_page_two.status_code == 200
