# path: returns/management/commands/seed_returnhub_demo.py
"""Seed a deterministic multi-surface demo environment for ReturnHub."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.constants import GROUP_NAMES, ROLE_ADMIN, ROLE_CUSTOMER, ROLE_MERCHANT, ROLE_OPS
from apps.returns.models import CustomerProfile, MerchantProfile, ReturnCase

User = get_user_model()


class Command(BaseCommand):
    """Create stable users, profiles, and cases for the Sprint 6 multi-surface demo."""

    help = "Seed deterministic users and paginated return cases for the ReturnHub demo."

    def handle(self, *args, **options):
        """Create demo users, groups, profiles, and enough cases for page 1 and page 2."""
        self._ensure_groups()

        admin_user = self._ensure_user(
            username="admin.demo",
            email="admin.demo@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        ops_user = self._ensure_user(
            username="ops.demo",
            email="ops.demo@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_OPS,
        )
        customer_one_user = self._ensure_user(
            username="customer.one",
            email="customer.one@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_CUSTOMER,
        )
        customer_two_user = self._ensure_user(
            username="customer.two",
            email="customer.two@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_CUSTOMER,
        )
        merchant_one_user = self._ensure_user(
            username="merchant.one",
            email="merchant.one@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_MERCHANT,
        )
        merchant_two_user = self._ensure_user(
            username="merchant.two",
            email="merchant.two@returnhub.local",
            password="ChangeMe123!",
            role=ROLE_MERCHANT,
        )

        customer_one = CustomerProfile.objects.update_or_create(
            user=customer_one_user,
            defaults={"full_name": "Customer One"},
        )[0]
        customer_two = CustomerProfile.objects.update_or_create(
            user=customer_two_user,
            defaults={"full_name": "Customer Two"},
        )[0]

        merchant_one = MerchantProfile.objects.update_or_create(
            user=merchant_one_user,
            defaults={"name": "Merchant One"},
        )[0]
        merchant_two = MerchantProfile.objects.update_or_create(
            user=merchant_two_user,
            defaults={"name": "Merchant Two"},
        )[0]

        self._ensure_cases(customer_one, merchant_one, start_index=1, count=16)
        self._ensure_cases(customer_two, merchant_two, start_index=17, count=16)

        self.stdout.write(self.style.SUCCESS("ReturnHub demo seed complete."))
        self.stdout.write(f"Admin user: {admin_user.username}")
        self.stdout.write(f"Ops user: {ops_user.username}")
        self.stdout.write(f"Customer users: {customer_one_user.username}, {customer_two_user.username}")
        self.stdout.write(f"Merchant users: {merchant_one_user.username}, {merchant_two_user.username}")
        self.stdout.write(f"Total cases: {ReturnCase.objects.count()}")

    def _ensure_groups(self):
        """Create required role groups if they do not already exist."""
        for group_name in GROUP_NAMES.values():
            Group.objects.get_or_create(name=group_name)

    def _ensure_user(self, username, email, password, role, is_staff=False, is_superuser=False):
        """Create or update a demo user and attach the correct group."""
        user, _ = User.objects.update_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        user.set_password(password)
        user.save()

        group = Group.objects.get(name=GROUP_NAMES[role])
        user.groups.set([group])
        return user

    def _ensure_cases(self, customer, merchant, start_index, count):
        """Create or update a fixed block of deterministic return cases."""
        statuses = ["new", "awaiting_customer", "in_review", "resolved"]

        for index in range(start_index, start_index + count):
            ReturnCase.objects.update_or_create(
                reference=f"RH-{index:05d}",
                defaults={
                    "customer": customer,
                    "merchant": merchant,
                    "status": statuses[(index - 1) % len(statuses)],
                    "priority": "medium" if index % 2 == 0 else "high",
                    "return_reason": "damaged_item" if index % 2 == 0 else "not_as_described",
                    "customer_message": f"Demo case {index} for deterministic pagination coverage.",
                    "sla_due_at": timezone.now() + timedelta(days=2),
                },
            )
