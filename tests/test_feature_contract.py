# path: tests/test_feature_contract.py
"""Unit tests for ReturnHub ML feature contract stability."""

from __future__ import annotations

import datetime
from collections import OrderedDict
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Group

from ml.features import (
    FEATURE_CONTRACT_VERSION,
    _delivery_to_return_days,
    _encode_item_category,
    _encode_return_reason,
    _hours_to_first_customer_evidence,
    _merchant_document_count,
    _message_length_bucket,
    _order_value_band,
    _order_value_band_high,
    _return_reason_is_damaged,
    _validate_feature_names,
    extract_case_features,
    load_feature_contract,
)
from tests.factories import (
    CustomerProfileFactory,
    MerchantProfileFactory,
    ReturnCaseFactory,
    UserFactory,
)


def add_group(user, group_name: str) -> None:
    """Attach a Django group to a user for test setup."""
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


@pytest.mark.django_db
def test_extracted_feature_names_match_committed_contract() -> None:
    """Feature extractor ordering must match the committed feature contract file."""
    customer_user = UserFactory(email="ml-feature@example.com")
    add_group(customer_user, "customer")
    customer_profile = CustomerProfileFactory(user=customer_user)
    merchant_profile = MerchantProfileFactory()

    prior_case = ReturnCaseFactory(customer=customer_profile)
    case = ReturnCaseFactory(
        customer=customer_profile,
        merchant=merchant_profile,
        item_category="electronics",
        return_reason="Damaged",
        customer_message="The product casing is split and the screen flickers intermittently.",
        order_value="549.00",
    )

    assert prior_case.pk != case.pk

    contract = load_feature_contract()
    features = extract_case_features(case)

    assert list(features.keys()) == contract["feature_names"]


def test_load_feature_contract_has_expected_version() -> None:
    """Committed contract version should match the extractor constant."""
    contract = load_feature_contract()

    assert contract["version"] == FEATURE_CONTRACT_VERSION


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (" apparel ", 1),
        ("electronics", 2),
        ("HOMEWARE", 3),
        ("beauty", 4),
        ("unknown-category", 99),
        ("", 99),
        (None, 99),
    ],
)
def test_encode_item_category_maps_known_and_unknown_values(raw_value, expected) -> None:
    """Item category encoding should normalize case and fall back to other."""
    assert _encode_item_category(raw_value) == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("damaged", 1),
        ("wrong_item", 2),
        ("wrong_size", 3),
        ("not_as_described", 4),
        ("changed_mind", 5),
        ("unexpected-reason", 99),
        ("", 99),
        (None, 99),
    ],
)
def test_encode_return_reason_maps_known_and_unknown_values(raw_value, expected) -> None:
    """Return reason encoding should normalize values and fall back to other."""
    assert _encode_return_reason(raw_value) == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("short note", 1),
        ("x" * 40, 2),
        ("x" * 120, 3),
        ("x" * 240, 4),
        ("   ", 1),
        (None, 1),
    ],
)
def test_message_length_bucket_covers_boundaries(raw_value, expected) -> None:
    """Message length bucketing should respect documented boundary cutoffs."""
    assert _message_length_bucket(raw_value) == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("49.99", 1),
        ("50.00", 2),
        ("149.99", 2),
        ("150.00", 3),
        ("399.99", 3),
        ("400.00", 4),
        (None, 1),
    ],
)
def test_order_value_band_covers_boundaries(raw_value, expected) -> None:
    """Order value banding should assign values into stable ordinal ranges."""
    assert _order_value_band(raw_value) == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("damaged", 1),
        ("wrong_item", 0),
        (None, 0),
    ],
)
def test_return_reason_is_damaged_flags_only_damaged_reasons(raw_value, expected) -> None:
    """Damaged-reason helper should emit a stable binary flag."""
    assert _return_reason_is_damaged(raw_value) == expected


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("399.99", 0),
        ("400.00", 1),
        (None, 0),
    ],
)
def test_order_value_band_high_flags_only_highest_band(raw_value, expected) -> None:
    """High-band helper should emit a stable binary flag."""
    assert _order_value_band_high(raw_value) == expected


def test_hours_to_first_customer_evidence_returns_zero_when_case_has_no_customer_document() -> None:
    """Missing customer evidence should yield a zero-hour delay."""

    class FakeQuerySet:
        def order_by(self, *args):
            return self

        def first(self):
            return None

    class FakeDocuments:
        def filter(self, **kwargs):
            assert kwargs == {"actor_role": "customer"}
            return FakeQuerySet()

    case = SimpleNamespace(
        created_at=datetime.datetime(2026, 4, 2, 10, 0, tzinfo=datetime.UTC),
        documents=FakeDocuments(),
    )

    assert _hours_to_first_customer_evidence(case) == 0.0


def test_hours_to_first_customer_evidence_clamps_negative_elapsed_time() -> None:
    """Evidence timestamps before case creation should clamp to zero hours."""

    class FakeQuerySet:
        def __init__(self, document):
            self.document = document

        def order_by(self, *args):
            return self

        def first(self):
            return self.document

    class FakeDocuments:
        def __init__(self, document):
            self.document = document

        def filter(self, **kwargs):
            assert kwargs == {"actor_role": "customer"}
            return FakeQuerySet(self.document)

    case_created_at = datetime.datetime(2026, 4, 2, 10, 0, tzinfo=datetime.UTC)
    first_document = SimpleNamespace(
        created_at=datetime.datetime(2026, 4, 2, 9, 0, tzinfo=datetime.UTC)
    )
    case = SimpleNamespace(created_at=case_created_at, documents=FakeDocuments(first_document))

    assert _hours_to_first_customer_evidence(case) == 0.0


def test_merchant_document_count_filters_merchant_documents() -> None:
    """Merchant document count should query the merchant role specifically."""

    class FakeQuerySet:
        def count(self):
            return 2

    class FakeDocuments:
        def filter(self, **kwargs):
            assert kwargs == {"actor_role": "merchant"}
            return FakeQuerySet()

    case = SimpleNamespace(documents=FakeDocuments())

    assert _merchant_document_count(case) == 2


def test_validate_feature_names_raises_on_contract_mismatch() -> None:
    """Feature vectors must match the committed contract order exactly."""
    with pytest.raises(ValueError, match="do not match the committed feature contract"):
        _validate_feature_names(OrderedDict([("unexpected_feature", 1)]))


@pytest.mark.django_db
def test_delivery_to_return_days_never_goes_negative() -> None:
    """Delivery-to-return lag should clamp future delivery dates to zero."""
    case = ReturnCaseFactory(delivery_date=datetime.date(2099, 1, 1))

    assert _delivery_to_return_days(case) == 0
