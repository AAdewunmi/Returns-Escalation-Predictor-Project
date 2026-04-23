"""Tests for authenticated console routes."""

from __future__ import annotations

import os

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from returns.models import ReturnCase
from tests.factories import (
    CustomerProfileFactory,
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
def test_ops_console_renders_counts_and_recent_cases(client) -> None:
    """Ops dashboard should render the current queue counts and recent cases."""
    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    submitted_case = ReturnCaseFactory(
        status=ReturnCase.Status.SUBMITTED,
        order_reference="OPS-1001",
        return_reason="Damaged item",
    )
    ReturnCaseFactory(status=ReturnCase.Status.IN_REVIEW, order_reference="OPS-1002")

    client.force_login(ops_user)
    response = client.get(reverse("console:ops-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert "Ops Console" in body
    assert "Submitted" in body
    assert "In review" in body
    assert submitted_case.order_reference in body
    assert f'href="/ops/{submitted_case.pk}/"' in body
    assert "Open case" in body


@pytest.mark.django_db
def test_ops_console_renders_ml_insights_panel(client) -> None:
    """Ops dashboard should expose persisted ML risk signals in-product."""
    ops_user = UserFactory()
    add_group(ops_user, "Ops")
    high_case = ReturnCaseFactory(
        status=ReturnCase.Status.SUBMITTED,
        order_reference="OPS-HIGH-RISK",
    )
    medium_case = ReturnCaseFactory(
        status=ReturnCase.Status.APPROVED,
        order_reference="OPS-MEDIUM-RISK",
    )
    low_case = ReturnCaseFactory(
        status=ReturnCase.Status.IN_REVIEW,
        order_reference="OPS-LOW-RISK",
    )
    RiskScoreFactory(
        case=high_case,
        label="high",
        model_version="model-high-v1",
        reason_codes=[{"code": "high_order_value"}, {"code": "delayed_return_window"}],
    )
    RiskScoreFactory(
        case=medium_case,
        label="medium",
        model_version="model-medium-v1",
        reason_codes=["high_order_value"],
    )
    RiskScoreFactory(case=low_case, label="low", model_version="model-low-v1")

    client.force_login(ops_user)
    response = client.get(reverse("console:ops-dashboard"))

    insights = response.context["ml_insights"]
    body = response.content.decode()
    assert response.status_code == 200
    assert insights["risk_distribution"] == {"low": 1, "medium": 1, "high": 1}
    assert insights["high_risk_active_count"] == 1
    assert insights["high_risk_queue_url"] == "/ops/?risk_label=high"
    assert insights["top_reason_codes"][0] == ("high_order_value", 2)
    assert "ML insights" in body
    assert "Review high-risk cases" in body
    assert 'href="/ops/?risk_label=high"' in body
    assert "OPS-HIGH-RISK" in body
    assert "Open analytics endpoint" not in body
    assert "/api/analytics/returns/" not in body


@pytest.mark.django_db
def test_customer_console_renders_only_customer_cases(client) -> None:
    """Customer dashboard should render recent cases tied to the current customer."""
    customer_profile = CustomerProfileFactory()
    add_group(customer_profile.user, "Customer")
    owned_case = ReturnCaseFactory(customer=customer_profile, order_reference="CUS-1001")
    ReturnCaseFactory(order_reference="CUS-9999")

    client.force_login(customer_profile.user)
    response = client.get(reverse("console:customer-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert owned_case.order_reference in body
    assert "CUS-9999" not in body
    assert f'href="/customer/{owned_case.pk}/"' in body
    assert "View my cases" not in body
    assert "Customer portal" not in body
    assert "View all cases" not in body
    assert "full case list" not in body
    assert "Open case" in body


@pytest.mark.django_db
def test_merchant_console_renders_only_merchant_cases(client) -> None:
    """Merchant dashboard should render recent cases tied to the current merchant."""
    merchant_profile = MerchantProfileFactory()
    add_group(merchant_profile.user, "Merchant")
    owned_case = ReturnCaseFactory(merchant=merchant_profile, order_reference="MER-1001")
    ReturnCaseFactory(order_reference="MER-9999")

    client.force_login(merchant_profile.user)
    response = client.get(reverse("console:merchant-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert owned_case.order_reference in body
    assert "MER-9999" not in body
    assert 'href="/merchant/"' in body
    assert f'href="/merchant/{owned_case.pk}/"' in body
    assert "Merchant portal" in body
    assert "View merchant cases" in body
    assert "Open case" in body


@pytest.mark.django_db
def test_console_routes_forbid_wrong_role(client) -> None:
    """Console routes should reject authenticated users without the required role."""
    customer_profile = CustomerProfileFactory()
    add_group(customer_profile.user, "Customer")

    client.force_login(customer_profile.user)
    response = client.get(reverse("console:ops-dashboard"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_console_renders_user_role_management_panel(client) -> None:
    """Admin dashboard should show user roles, status, last login, and admin links."""
    admin_user = UserFactory(
        username="admin.panel",
        email="admin.panel@example.com",
        is_superuser=True,
        is_staff=True,
        last_login=timezone.now(),
    )
    add_group(admin_user, "Admin")
    ops_user = UserFactory(
        username="ops.panel",
        email="ops.panel@example.com",
        is_active=False,
    )
    add_group(ops_user, "Ops")

    client.force_login(admin_user)
    response = client.get(reverse("console:admin-dashboard"))

    rows = {row["user"].username: row for row in response.context["user_management_rows"]}
    body = response.content.decode()
    assert response.status_code == 200
    assert rows["admin.panel"]["roles"] == "Admin"
    assert rows["ops.panel"]["roles"] == "Ops"
    assert rows["ops.panel"]["is_active"] is False
    assert rows["ops.panel"]["admin_url"] == f"/admin/auth/user/{ops_user.pk}/change/"
    assert "User management" in body
    assert "Platform users" in body
    assert "admin.panel@example.com" in body
    assert "ops.panel@example.com" in body
    assert "Inactive" in body
    assert "Never" in body
    assert f'href="/admin/auth/user/{ops_user.pk}/change/"' in body


@pytest.mark.django_db
def test_admin_console_renders_health_and_release_panel(client, settings, monkeypatch) -> None:
    """Admin dashboard should show readiness, release, settings, and database state."""
    admin_user = UserFactory(is_superuser=True, is_staff=True)
    add_group(admin_user, "Admin")
    settings.RELEASE_VERSION = "test-release-1"
    monkeypatch.setattr(
        "console.views.get_readiness_payload",
        lambda: {
            "status": "ok",
            "service": "returnhub",
            "release": "test-release-1",
            "timestamp": "2026-04-23T09:00:00+00:00",
            "checks": {"database": "ok"},
        },
    )

    client.force_login(admin_user)
    response = client.get(reverse("console:admin-dashboard"))

    panel = response.context["health_release_panel"]
    body = response.content.decode()
    assert response.status_code == 200
    expected_settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "unknown")
    assert panel == {
        "status": "ok",
        "release": "test-release-1",
        "settings_module": expected_settings_module,
        "database": "ok",
    }
    assert "Health and release" in body
    assert "test-release-1" in body
    assert expected_settings_module in body
    assert "Connected" in body


@pytest.mark.django_db
def test_admin_console_health_panel_renders_degraded_database(client, monkeypatch) -> None:
    """The health panel should expose degraded database readiness clearly."""
    admin_user = UserFactory(is_superuser=True, is_staff=True)
    add_group(admin_user, "Admin")
    monkeypatch.setattr(
        "console.views.get_readiness_payload",
        lambda: {
            "status": "degraded",
            "service": "returnhub",
            "release": "degraded-release",
            "timestamp": "2026-04-23T09:00:00+00:00",
            "checks": {"database": "unavailable"},
        },
    )

    client.force_login(admin_user)
    response = client.get(reverse("console:admin-dashboard"))

    body = response.content.decode()
    assert response.status_code == 200
    assert response.context["health_release_panel"]["status"] == "degraded"
    assert response.context["health_release_panel"]["database"] == "unavailable"
    assert "Degraded" in body
    assert "Unavailable" in body


@pytest.mark.django_db
def test_superuser_without_admin_group_gets_403_on_ops_console(client) -> None:
    """Superusers without the admin role should not bypass non-admin console boundaries."""
    admin_user = UserFactory(is_superuser=True, is_staff=True)

    client.force_login(admin_user)
    response = client.get(reverse("console:ops-dashboard"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_customer_console_handles_customer_user_without_profile(client) -> None:
    """Customer dashboard should render an empty state when no customer profile exists."""
    customer_user = UserFactory(email="customer-no-profile@example.com")
    add_group(customer_user, "Customer")

    client.force_login(customer_user)
    response = client.get(reverse("console:customer-dashboard"))

    assert response.status_code == 200
    assert "No customer cases yet" in response.content.decode()


@pytest.mark.django_db
def test_merchant_console_handles_merchant_user_without_profile(client) -> None:
    """Merchant dashboard should render an empty state when no merchant profile exists."""
    merchant_user = UserFactory(email="merchant-no-profile@example.com")
    add_group(merchant_user, "Merchant")

    client.force_login(merchant_user)
    response = client.get(reverse("console:merchant-dashboard"))

    assert response.status_code == 200
    assert "No merchant-linked cases yet" in response.content.decode()
