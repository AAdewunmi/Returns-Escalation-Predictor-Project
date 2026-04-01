# path: returns/migrations/0007_expand_evidence_document_metadata.py
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("returns", "0006_sprint3_risk_baseline"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidencedocument",
            name="checksum_sha256",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="content_type",
            field=models.CharField(default="application/octet-stream", max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="document_kind",
            field=models.CharField(
                choices=[
                    ("customer_evidence", "Customer evidence"),
                    ("merchant_response", "Merchant response"),
                    ("ops_attachment", "Ops attachment"),
                ],
                default="customer_evidence",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="note",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="original_filename",
            field=models.CharField(default="uploaded-file", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="size_bytes",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="uploaded_by_role",
            field=models.CharField(default="unknown", max_length=32),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="visible_to_customer",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="visible_to_merchant",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterModelOptions(
            name="evidencedocument",
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="evidencedocument",
            constraint=models.CheckConstraint(
                check=models.Q(("size_bytes__gte", 0)),
                name="returns_evidencedocument_size_non_negative",
            ),
        ),
    ]
