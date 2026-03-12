# path: accounts/models.py
"""Profile models used to represent customer and merchant identities."""
from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class CustomerProfile(TimeStampedModel):
    """Represents a customer that owns return cases."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    external_reference = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=120)

    class Meta:
        """Meta configuration for customer profiles."""

        ordering = ["display_name"]

    def __str__(self) -> str:
        """Return a readable representation for the admin and shell."""
        return f"CustomerProfile<{self.external_reference}>"


class MerchantProfile(TimeStampedModel):
    """Represents a merchant account associated with return cases."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="merchant_profile",
    )
    merchant_code = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=120)
    support_email = models.EmailField()

    class Meta:
        """Meta configuration for merchant profiles."""

        ordering = ["display_name"]

    def __str__(self) -> str:
        """Return a readable representation for the admin and shell."""
        return f"MerchantProfile<{self.merchant_code}>"
