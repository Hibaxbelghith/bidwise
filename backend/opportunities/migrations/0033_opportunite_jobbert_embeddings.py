from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0032_opportunite_normalized_skills_opportunite_raw_skills_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="jobbert_embedding_model",
            field=models.CharField(blank=True, db_index=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="jobbert_embedding_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="jobbert_embedding_vector",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
