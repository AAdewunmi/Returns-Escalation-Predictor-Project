# path: tests/unit/ml/test_feature_contract.py
"""Unit tests for ReturnHub ML feature contract stability."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from ml.features import extract_case_features, load_feature_contract
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
