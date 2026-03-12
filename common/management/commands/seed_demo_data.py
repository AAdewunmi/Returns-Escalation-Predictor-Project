# path: common/management/commands/seed_demo_data.py
"""Seed deterministic demo data for local development and manual testing."""
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import CustomerProfile, MerchantProfile
from returns.models import CaseEvent, ReturnCase


class Command(BaseCommand):
    """Create stable demo users, groups, and return cases."""

    help = "Seed deterministic demo users, groups, and return cases."

    GROUP_NAMES = ["Admin", "Ops", "Customer", "Merchant"]

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        """Execute the seed routine."""
        groups = self._ensure_groups()
        users = self._ensure_users(groups)
        self._ensure_profiles(users)
        created_case_count = self._ensure_return_cases(users)
        self.stdout.write(
            self.style.SUCCESS(f"Seed complete. Stable return case count: {created_case_count}")
        )

    def _ensure_groups(self) -> dict[str, Group]:
        """Create the role groups used across product surfaces."""
        return {
            name: Group.objects.get_or_create(name=name)[0]
            for name in self.GROUP_NAMES
        }

    def _ensure_users(self, groups: dict[str, Group]) -> dict[str, object]:
        """Create deterministic demo users and group assignments."""
        user_model = get_user_model()

        admin_user, _ = user_model.objects.update_or_create(
            username="admin",
            defaults={
                "email": "admin@returnhub.local",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password("password123")
        admin_user.save()
        admin_user.groups.set([groups["Admin"]])

        ops_user, _ = user_model.objects.update_or_create(
            username="ops",
            defaults={"email": "ops@returnhub.local", "is_staff": False, "is_superuser": False},
        )
        ops_user.set_password("password123")
        ops_user.save()
        ops_user.groups.set([groups["Ops"]])

        customer_user, _ = user_model.objects.update_or_create(
            username="customer",
            defaults={"email": "customer@returnhub.local", "is_staff": False, "is_superuser": False},
        )
        customer_user.set_password("password123")
        customer_user.save()
        customer_user.groups.set([groups["Customer"]])

        merchant_user, _ = user_model.objects.update_or_create(
            username="merchant",
            defaults={"email": "merchant@returnhub.local", "is_staff": False, "is_superuser": False},
        )
        merchant_user.set_password("password123")
        merchant_user.save()
        merchant_user.groups.set([groups["Merchant"]])

        return {
            "admin": admin_user,
            "ops": ops_user,
            "customer": customer_user,
            "merchant": merchant_user,
        }

    def _ensure_profiles(self, users: dict[str, object]) -> None:
        """Create deterministic profile records for customer and merchant users."""
        CustomerProfile.objects.update_or_create(
            user=users["customer"],
            defaults={
                "external_reference": "CUS-0001",
                "display_name": "Demo Customer",
            },
        )
        MerchantProfile.objects.update_or_create(
            user=users["merchant"],
            defaults={
                "merchant_code": "MER-0001",
                "display_name": "Demo Merchant",
                "support_email": "support@merchant.local",
            },
        )

    def _ensure_return_cases(self, users: dict[str, object]) -> int:
        """Create enough stable return cases to exercise pagination later."""
        customer_profile = CustomerProfile.objects.get(user=users["customer"])
        merchant_profile = MerchantProfile.objects.get(user=users["merchant"])

        base_now = timezone.make_aware(datetime(2026, 1, 6, 9, 0, 0))
        base_delivery_date = date(2025, 12, 20)

        statuses = [
            ReturnCase.Status.SUBMITTED,
            ReturnCase.Status.IN_REVIEW,
            ReturnCase.Status.WAITING_CUSTOMER,
            ReturnCase.Status.WAITING_MERCHANT,
            ReturnCase.Status.APPROVED,
            ReturnCase.Status.REJECTED,
        ]
        priorities = [
            ReturnCase.Priority.LOW,
            ReturnCase.Priority.MEDIUM,
            ReturnCase.Priority.HIGH,
            ReturnCase.Priority.URGENT,
        ]

        for index in range(1, 33):
            case, _ = ReturnCase.objects.update_or_create(
                order_reference=f"RH-{index:04d}",
                defaults={
                    "customer": customer_profile,
                    "merchant": merchant_profile,
                    "item_category": "apparel" if index % 2 == 0 else "electronics",
                    "return_reason": "Damaged item" if index % 3 == 0 else "Wrong size",
                    "customer_message": f"Seeded customer message {index}",
                    "order_value": f"{49 + index}.99",
                    "delivery_date": base_delivery_date + timedelta(days=index),
                    "status": statuses[(index - 1) % len(statuses)],
                    "priority": priorities[(index - 1) % len(priorities)],
                    "sla_due_at": base_now + timedelta(days=index),
                    "last_status_changed_at": base_now + timedelta(hours=index),
                },
            )

            CaseEvent.objects.get_or_create(
                return_case=case,
                event_type="seed_case_created",
                defaults={
                    "actor": users["ops"],
                    "actor_role": "ops",
                    "payload": {
                        "seed_index": index,
                        "order_reference": case.order_reference,
                    },
                },
            )

        return ReturnCase.objects.count()
