# path: common/models.py
"""Shared model primitives used across project apps."""
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model that adds creation and update timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta configuration for the abstract base model."""

        abstract = True
