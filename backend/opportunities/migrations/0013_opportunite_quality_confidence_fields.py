from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0012_opportunite_ville"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="date_confidence",
            field=models.CharField(
                choices=[
                    ("EXACT", "Exacte"),
                    ("ESTIMATED", "Estimée"),
                    ("FALLBACK", "Fallback"),
                ],
                db_index=True,
                default="FALLBACK",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="quality_score",
            field=models.FloatField(db_index=True, default=0.0),
        ),
    ]
