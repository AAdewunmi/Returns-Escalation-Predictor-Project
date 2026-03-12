"""Tests for query-string template tag helpers."""

from django.http import QueryDict

from common.templatetags.querystring import replace_query


def test_replace_query_preserves_existing_values_when_no_kwargs():
    """Tag should keep existing query parameters when no replacements are given."""
    context = {
        "request": type("Request", (), {"GET": QueryDict("status=open&page=2")})(),
    }

    assert replace_query(context) == "status=open&page=2"


def test_replace_query_updates_existing_value_and_adds_new_value():
    """Tag should update existing keys and append new keys."""
    context = {
        "request": type("Request", (), {"GET": QueryDict("status=open&page=2")})(),
    }

    encoded = replace_query(context, page=3, sort="created_at")

    assert "status=open" in encoded
    assert "page=3" in encoded
    assert "sort=created_at" in encoded


def test_replace_query_removes_key_when_value_is_none():
    """Tag should remove keys when replacement value is None."""
    context = {
        "request": type("Request", (), {"GET": QueryDict("status=open&page=2&sort=created_at")})(),
    }

    encoded = replace_query(context, sort=None)

    assert "status=open" in encoded
    assert "page=2" in encoded
    assert "sort=created_at" not in encoded
