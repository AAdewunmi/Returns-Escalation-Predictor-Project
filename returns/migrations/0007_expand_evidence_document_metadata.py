"""Compatibility placeholder for the evidence metadata migration slot."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("returns", "0003_evidencedocument_metadata"),
    ]

    operations = []
