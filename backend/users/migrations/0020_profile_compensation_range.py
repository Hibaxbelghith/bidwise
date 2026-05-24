# Generated manually for onboarding compensation range support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0019_auditlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="compensation_min_expectation",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Minimum expected compensation amount",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profil",
            name="compensation_max_expectation",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Maximum expected compensation amount",
                null=True,
            ),
        ),
    ]
