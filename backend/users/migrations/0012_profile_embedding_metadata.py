from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_profile_resume_completion_salary_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="embedding_model",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Embedding model identifier used for the cached profile vector",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="profil",
            name="embedding_dimensions",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Dimension count of the cached profile embedding vector",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profil",
            name="embedding_updated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Last time the versioned profile embedding metadata was updated",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profil",
            name="embedding_content_hash",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Deterministic hash of semantic profile content used for embeddings",
                max_length=64,
            ),
        ),
    ]
