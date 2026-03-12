# path: returns/migrations/0001_initial.py
"""Initial returns migration."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the core returns workflow models."""

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReturnCase",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order_reference", models.CharField(max_length=64, unique=True)),
                ("item_category", models.CharField(max_length=80)),
                ("return_reason", models.CharField(max_length=120)),
                ("customer_message", models.TextField(blank=True)),
                ("order_value", models.DecimalField(decimal_places=2, max_digits=10)),
                ("delivery_date", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("submitted", "Submitted"),
                            ("in_review", "In review"),
                            ("waiting_customer", "Waiting for customer"),
                            ("waiting_merchant", "Waiting for merchant"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="submitted",
                        max_length=32,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="medium",
                        max_length=16,
                    ),
                ),
                ("sla_due_at", models.DateTimeField(blank=True, null=True)),
                ("last_status_changed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="return_cases",
                        to="accounts.customerprofile",
                    ),
                ),
                (
                    "merchant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="return_cases",
                        to="accounts.merchantprofile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.CreateModel(
            name="EvidenceDocument",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "actor_role",
                    models.CharField(
                        choices=[
                            ("customer", "Customer"),
                            ("merchant", "Merchant"),
                            ("ops", "Ops"),
                            ("admin", "Admin"),
                        ],
                        max_length=16,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[("evidence", "Evidence"), ("response", "Response")],
                        max_length=16,
                    ),
                ),
                ("file_path", models.CharField(max_length=255)),
                ("original_filename", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=120)),
                ("byte_size", models.PositiveIntegerField()),
                ("notes", models.CharField(blank=True, max_length=255)),
                (
                    "return_case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="documents",
                        to="returns.returncase",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="uploaded_documents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.CreateModel(
            name="CaseNote",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("body", models.TextField()),
                ("is_internal", models.BooleanField(default=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="case_notes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "return_case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes",
                        to="returns.returncase",
                    ),
                ),
            ],
            options={"ordering": ["-created_at", "id"]},
        ),
        migrations.CreateModel(
            name="CaseEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor_role", models.CharField(blank=True, max_length=16)),
                ("event_type", models.CharField(max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="case_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "return_case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="returns.returncase",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
