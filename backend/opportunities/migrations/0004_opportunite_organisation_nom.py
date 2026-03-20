# Generated manually for backward-compatible organization text support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0003_opportunity_constraints_and_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="organisation_nom",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]

