from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0005_opportunite_embeddings"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
