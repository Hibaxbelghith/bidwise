from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0034_remove_esco_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="content_fingerprint",
            field=models.CharField(blank=True, db_index=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="duplicate_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="duplicate_versions",
                to="opportunities.opportunite",
            ),
        ),
    ]
