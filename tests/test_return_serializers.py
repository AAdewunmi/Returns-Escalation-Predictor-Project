"""Tests for returns API serializers."""

import datetime
from decimal import Decimal

import pytest
from django.test import RequestFactory

from returns.api.serializers import (
    CaseNoteCreateSerializer,
    CaseNoteSerializer,
    ReturnCaseCreateSerializer,
    ReturnCaseDetailSerializer,
    ReturnCaseStatusUpdateSerializer,
)
from returns.models import ReturnCase, RiskScore
from returns.services.cases import ReturnCaseCreateInput, StatusUpdateInput
from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_return_case_create_serializer_validates_positive_order_value() -> None:
    """Order value must be greater than zero."""
    merchant = MerchantProfileFactory()

    serializer = ReturnCaseCreateSerializer(
        data={
            "merchant_id": merchant.pk,
            "external_order_ref": "ORD-1001",
            "item_category": "apparel",
            "return_reason": "damaged",
            "customer_message": "Need help",
            "order_value": "0.00",
            "delivery_date": "2025-01-10",
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors["order_value"] == ["Order value must be greater than zero."]


@pytest.mark.django_db
def test_return_case_create_serializer_rejects_future_delivery_date() -> None:
    """Delivery date cannot be in the future."""
    merchant = MerchantProfileFactory()
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)

    serializer = ReturnCaseCreateSerializer(
        data={
            "merchant_id": merchant.pk,
            "external_order_ref": "ORD-1002",
            "item_category": "apparel",
            "return_reason": "damaged",
            "customer_message": "Need help",
            "order_value": "10.00",
            "delivery_date": tomorrow.isoformat(),
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors["delivery_date"] == ["Delivery date cannot be in the future."]


@pytest.mark.django_db
def test_return_case_create_serializer_rejects_blank_customer_message() -> None:
    """Customer message must contain non-whitespace content."""
    merchant = MerchantProfileFactory()

    serializer = ReturnCaseCreateSerializer(
        data={
            "merchant_id": merchant.pk,
            "external_order_ref": "ORD-1003",
            "item_category": "apparel",
            "return_reason": "damaged",
            "customer_message": "   ",
            "order_value": "10.00",
            "delivery_date": "2025-01-10",
        }
    )

    assert serializer.is_valid() is False
    assert serializer.errors["customer_message"] == ["Customer message cannot be empty."]


@pytest.mark.django_db
def test_return_case_create_serializer_calls_workflow_service(monkeypatch) -> None:
    """Validated create requests should call the workflow service with structured input."""
    merchant = MerchantProfileFactory()
    actor = UserFactory()
    request = RequestFactory().post("/returns/")
    request.user = actor
    expected_case = ReturnCaseFactory()

    captured: dict[str, object] = {}

    def fake_create_return_case(*, actor, input_data):
        captured["actor"] = actor
        captured["input_data"] = input_data
        return expected_case

    monkeypatch.setattr(
        "returns.api.serializers.create_return_case",
        fake_create_return_case,
    )

    serializer = ReturnCaseCreateSerializer(
        data={
            "merchant_id": merchant.pk,
            "external_order_ref": "ORD-1004",
            "item_category": "apparel",
            "return_reason": "damaged",
            "customer_message": "Need help",
            "order_value": "10.00",
            "delivery_date": "2025-01-10",
        },
        context={"request": request},
    )

    assert serializer.is_valid(), serializer.errors
    created_case = serializer.save()

    assert created_case == expected_case
    assert captured["actor"] == actor
    assert captured["input_data"] == ReturnCaseCreateInput(
        merchant_profile=merchant,
        external_order_ref="ORD-1004",
        item_category="apparel",
        return_reason="damaged",
        customer_message="Need help",
        order_value=Decimal("10.00"),
        delivery_date=datetime.date(2025, 1, 10),
    )


def test_return_case_status_update_serializer_builds_service_input() -> None:
    """Validated status payloads should convert to the service DTO."""
    serializer = ReturnCaseStatusUpdateSerializer(
        data={
            "status": ReturnCase.Status.IN_REVIEW,
            "priority": ReturnCase.Priority.HIGH,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.to_service_input() == StatusUpdateInput(
        status=ReturnCase.Status.IN_REVIEW,
        priority=ReturnCase.Priority.HIGH,
    )


def test_return_case_status_update_serializer_allows_null_priority() -> None:
    """Priority may be omitted or explicitly null."""
    serializer = ReturnCaseStatusUpdateSerializer(
        data={
            "status": ReturnCase.Status.APPROVED,
            "priority": None,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.to_service_input() == StatusUpdateInput(
        status=ReturnCase.Status.APPROVED,
        priority=None,
    )


def test_case_note_create_serializer_rejects_blank_body() -> None:
    """Blank note bodies should be rejected."""
    serializer = CaseNoteCreateSerializer(data={"body": "   "})

    assert serializer.is_valid() is False
    assert serializer.errors["body"] == ["Note body cannot be empty."]


def test_case_note_create_serializer_accepts_non_blank_body() -> None:
    """Non-empty note content should validate."""
    serializer = CaseNoteCreateSerializer(data={"body": "Follow up with merchant"})

    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_case_note_serializer_exposes_author_email() -> None:
    """Case-note responses should include author email."""
    case = ReturnCaseFactory()
    author = UserFactory(email="ops@example.com")
    note = case.notes.model.objects.create(return_case=case, author=author, body="Internal note")

    data = CaseNoteSerializer(note).data

    assert data["body"] == "Internal note"
    assert data["author_email"] == "ops@example.com"
    assert "created_at" in data


@pytest.mark.django_db
def test_return_case_detail_serializer_exposes_current_domain_fields() -> None:
    """Case detail responses should use the current merchant and customer relations."""
    case = ReturnCaseFactory(
        order_reference="ORD-2001",
        item_category="apparel",
        return_reason="damaged",
        customer_message="Need help",
        order_value=Decimal("59.99"),
    )
    case.customer.user.email = "customer@example.com"
    case.customer.user.save(update_fields=["email"])

    data = ReturnCaseDetailSerializer(case).data

    assert data["order_reference"] == "ORD-2001"
    assert data["merchant_name"] == case.merchant.display_name
    assert data["customer_email"] == "customer@example.com"
    assert data["status"] == case.status
    assert data["priority"] == case.priority
    assert data["risk"] is None


@pytest.mark.django_db
def test_return_case_detail_serializer_exposes_risk_to_ops_users() -> None:
    """Ops users should receive persisted risk payloads in case detail responses."""
    case = ReturnCaseFactory()
    ops_user = UserFactory()
    RiskScore.objects.create(
        case=case,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.74"),
        label="high",
        reason_codes=[{"code": "high_order_value", "direction": "up", "detail": "High value."}],
        scored_at=datetime.datetime(2025, 1, 11, 9, 0, 0, tzinfo=datetime.UTC),
    )
    request = RequestFactory().get(f"/api/returns/{case.pk}/")
    request.user = ops_user

    monkeypatch_group = pytest.MonkeyPatch()
    monkeypatch_group.setattr("returns.api.serializers.is_ops", lambda user: True)
    monkeypatch_group.setattr("returns.api.serializers.is_admin", lambda user: False)
    try:
        data = ReturnCaseDetailSerializer(case, context={"request": request}).data
    finally:
        monkeypatch_group.undo()

    assert data["risk"]["model_version"] == "return-risk-placeholder-v1"
    assert data["risk"]["label"] == "high"
    assert data["risk"]["score"] == "0.74"


@pytest.mark.django_db
def test_return_case_detail_serializer_hides_risk_from_customers() -> None:
    """Non-ops and non-admin users should not receive risk payloads."""
    customer_profile = CustomerProfileFactory()
    case = ReturnCaseFactory(customer=customer_profile)
    RiskScore.objects.create(
        case=case,
        model_version="return-risk-placeholder-v1",
        score=Decimal("0.40"),
        label="medium",
        reason_codes=[],
        scored_at=datetime.datetime(2025, 1, 11, 9, 0, 0, tzinfo=datetime.UTC),
    )
    request = RequestFactory().get(f"/api/returns/{case.pk}/")
    request.user = customer_profile.user

    data = ReturnCaseDetailSerializer(case, context={"request": request}).data

    assert data["risk"] is None


@pytest.mark.django_db
def test_case_note_create_serializer_calls_service(monkeypatch) -> None:
    """Note-create serializer should delegate to the workflow service."""
    actor = UserFactory()
    case = ReturnCaseFactory()
    serializer = CaseNoteCreateSerializer(data={"body": "Escalated"})
    expected_note = case.notes.model(return_case=case, author=actor, body="Escalated")
    captured: dict[str, object] = {}

    def fake_add_case_note(*, actor, case, body):
        captured["actor"] = actor
        captured["case"] = case
        captured["body"] = body
        return expected_note

    monkeypatch.setattr("returns.api.serializers.add_case_note", fake_add_case_note)

    assert serializer.is_valid(), serializer.errors
    note = serializer.create_note(actor=actor, case=case)

    assert note == expected_note
    assert captured == {"actor": actor, "case": case, "body": "Escalated"}


@pytest.mark.django_db
def test_return_case_detail_serializer_create_note_calls_service(monkeypatch) -> None:
    """Detail serializer should delegate note creation to the workflow service."""
    actor = UserFactory()
    case = ReturnCaseFactory()
    expected_note = case.notes.model(return_case=case, author=actor, body="Escalated")
    captured: dict[str, object] = {}

    def fake_add_case_note(*, actor, case, body):
        captured["actor"] = actor
        captured["case"] = case
        captured["body"] = body
        return expected_note

    monkeypatch.setattr(
        "returns.api.serializers.add_case_note",
        fake_add_case_note,
    )

    serializer = ReturnCaseDetailSerializer(instance=case)
    serializer._validated_data = {"body": "Escalated"}

    note = serializer.create_note(actor=actor, case=case)

    assert note == expected_note
    assert captured == {"actor": actor, "case": case, "body": "Escalated"}
