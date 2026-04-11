from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0011_opportunite_embedding_vector_pg_ivfflat"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="ville",
            field=models.CharField(blank=True, db_index=True, default="", max_length=120),
        ),
    ]
