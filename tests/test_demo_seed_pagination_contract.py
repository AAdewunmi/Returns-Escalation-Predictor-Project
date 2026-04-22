# path: tests/test_demo_seed_pagination_contract.py
"""Integration tests for demo-seed pagination guarantees across product surfaces."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from returns.models import ReturnCase

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_seed_returnhub_demo_creates_page_two_capacity_across_roles() -> None:
    """The preferred demo seed should create enough cases for second-page walkthroughs."""

    call_command("seed_returnhub_demo")

    assert ReturnCase.objects.count() == 32
    assert ReturnCase.objects.filter(customer__user__username="customer.one").count() == 16
    assert ReturnCase.objects.filter(customer__user__username="customer.two").count() == 16
    assert ReturnCase.objects.filter(merchant__user__username="merchant.one").count() == 16
    assert ReturnCase.objects.filter(merchant__user__username="merchant.two").count() == 16


def test_ops_queue_seeded_surface_renders_page_one_and_page_two(client) -> None:
    """The standalone ops queue should render both pages with seeded demo data."""

    call_command("seed_returnhub_demo")
    ops_user = User.objects.get(username="ops.demo")

    client.force_login(ops_user)

    page_one = client.get(reverse("ops:queue"), {"page": 1})
    page_two = client.get(reverse("ops:queue"), {"page": 2})

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert b"Showing 1-15 of 32" in page_one.content
    assert b"Showing 16-30 of 32" in page_two.content


def test_customer_and_merchant_seeded_surfaces_render_second_page(client) -> None:
    """Customer and merchant list pages should both render page two after demo seeding."""

    call_command("seed_returnhub_demo")

    customer_user = User.objects.get(username="customer.one")
    merchant_user = User.objects.get(username="merchant.one")

    client.force_login(customer_user)
    customer_page_two = client.get(reverse("customer_portal:case_list"), {"page": 2})

    assert customer_page_two.status_code == 200
    assert b"Showing 16-16 of 16" in customer_page_two.content

    client.logout()

    client.force_login(merchant_user)
    merchant_page_two = client.get(reverse("merchant_portal:case_list"), {"page": 2})

    assert merchant_page_two.status_code == 200
    assert b"Showing 16-16 of 16" in merchant_page_two.content
