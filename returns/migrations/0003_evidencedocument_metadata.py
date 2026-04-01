from django.db import migrations, models

import returns.models


class Migration(migrations.Migration):

    dependencies = [
        ("returns", "0002_riskscore"),
    ]

    operations = [
        migrations.AddField(
            model_name="evidencedocument",
            name="checksum_sha256",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="evidencedocument",
            name="file",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=returns.models.build_document_upload_path,
            ),
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
    ]
