from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_profile_ml_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="embedding_features_hash",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Hash of the normalized profile features used for the cached embedding",
                max_length=64,
            ),
        ),
    ]
