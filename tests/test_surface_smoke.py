# path: tests/test_surface_smoke.py
"""Cross-surface smoke tests for the ReturnHub product shell."""

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


@pytest.fixture()
def seeded_data():
    """Create deterministic demo data for smoke checks."""
    call_command("seed_returnhub_demo")


def login(client, path, username):
    """Post credentials to the requested login path."""
    return client.post(
        path,
        {"username": username, "password": "ChangeMe123!"},
    )


def test_admin_can_open_admin_console(client, seeded_data):
    """Admin should reach the admin console."""
    login_response = login(client, "/login/admin/", "admin.demo")
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/console/admin/"

    console_response = client.get("/console/admin/")

    assert console_response.status_code == 200


def test_admin_can_open_customer_portal_pages(client, seeded_data):
    """Admin should be able to inspect customer portal page 1 and page 2."""
    login_response = login(client, "/login/admin/", "admin.demo")
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/console/admin/"

    customer_page_1 = client.get("/customer/?page=1")
    customer_page_2 = client.get("/customer/?page=2")

    assert customer_page_1.status_code == 200
    assert customer_page_2.status_code == 200


def test_ops_can_open_console_and_ops_page_one_and_two(client, seeded_data):
    """Ops should reach the ops console and queue pages 1 and 2."""
    login_response = login(client, "/login/ops/", "ops.demo")
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/console/ops/"

    console_response = client.get("/console/ops/")
    ops_page_1 = client.get("/ops/?page=1")
    ops_page_2 = client.get("/ops/?page=2")

    assert console_response.status_code == 200
    assert ops_page_1.status_code == 200
    assert ops_page_2.status_code == 200


def test_customer_can_open_console_and_customer_pages_one_and_two(client, seeded_data):
    """Customer should reach the customer console and customer list pages 1 and 2."""
    login_response = login(client, "/login/customer/", "customer.one")
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/console/customer/"

    console_response = client.get("/console/customer/")
    customer_page_1 = client.get("/customer/?page=1")
    customer_page_2 = client.get("/customer/?page=2")

    assert console_response.status_code == 200
    assert customer_page_1.status_code == 200
    assert customer_page_2.status_code == 200
    assert b"Showing 1-15 of 16" in customer_page_1.content
    assert b"Showing 16-16 of 16" in customer_page_2.content


def test_merchant_can_open_console_and_merchant_pages_one_and_two(client, seeded_data):
    """Merchant should reach the merchant console and merchant list pages 1 and 2."""
    login_response = login(client, "/login/merchant/", "merchant.one")
    assert login_response.status_code == 302
    assert login_response.headers["Location"] == "/console/merchant/"

    console_response = client.get("/console/merchant/")
    merchant_page_1 = client.get("/merchant/?page=1")
    merchant_page_2 = client.get("/merchant/?page=2")

    assert console_response.status_code == 200
    assert merchant_page_1.status_code == 200
    assert merchant_page_2.status_code == 200
    assert b"Showing 1-15 of 16" in merchant_page_1.content
    assert b"Showing 16-16 of 16" in merchant_page_2.content
