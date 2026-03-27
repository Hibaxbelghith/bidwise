from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("opportunities", "0004_opportunite_organisation_nom"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="embedding_model",
            field=models.CharField(blank=True, db_index=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="embedding_vector",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
