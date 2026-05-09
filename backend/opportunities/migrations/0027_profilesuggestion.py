from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0026_opportunite_normalized_employment_db_defaults"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfileSuggestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "term_type",
                    models.CharField(
                        choices=[("SKILL", "Skill"), ("ROLE", "Role")],
                        db_index=True,
                        max_length=16,
                    ),
                ),
                ("canonical", models.CharField(max_length=160)),
                ("normalized_key", models.CharField(max_length=180)),
                ("aliases", models.JSONField(blank=True, default=list)),
                ("frequency", models.PositiveIntegerField(db_index=True, default=0)),
                ("confidence", models.FloatField(db_index=True, default=0.0)),
                ("language_counts", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_built_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["term_type", "-frequency", "canonical"],
            },
        ),
        migrations.AddConstraint(
            model_name="profilesuggestion",
            constraint=models.UniqueConstraint(
                fields=("term_type", "normalized_key"),
                name="uniq_profile_suggestion_type_key",
            ),
        ),
        migrations.AddIndex(
            model_name="profilesuggestion",
            index=models.Index(
                fields=["term_type", "is_active", "-frequency"],
                name="prof_sugg_type_act_freq_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="profilesuggestion",
            index=models.Index(
                fields=["term_type", "normalized_key"],
                name="profile_sugg_type_key_idx",
            ),
        ),
    ]
