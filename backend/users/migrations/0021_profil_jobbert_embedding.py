from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0020_profile_compensation_range"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="jobbert_embedding",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profil",
            name="jobbert_embedding_content_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="profil",
            name="jobbert_embedding_model",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="profil",
            name="jobbert_embedding_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
