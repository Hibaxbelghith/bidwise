# Generated manually for profile resume and Tunisia compensation defaults.

import django.db.models.deletion
import users.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_profile_employment_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="compensation_currency",
            field=models.CharField(
                blank=True,
                default="TND",
                help_text="ISO currency code for expected compensation",
                max_length=3,
            ),
        ),
        migrations.AlterField(
            model_name="profil",
            name="compensation_period",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MONTHLY", "Monthly"),
                    ("YEARLY", "Yearly"),
                    ("DAILY", "Daily"),
                    ("HOURLY", "Hourly"),
                ],
                help_text="Compensation period",
                max_length=10,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="ProfileResume",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(blank=True, null=True, upload_to=users.models.profile_resume_upload_to)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("parsed_text", models.TextField(blank=True, default="")),
                (
                    "resume_text_embedding_source",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Clean deterministic resume text source prepared for future embeddings",
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[("UPLOAD", "Upload"), ("BUILDER", "BidWise Builder")],
                        db_index=True,
                        default="UPLOAD",
                        max_length=16,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resumes",
                        to="users.profil",
                    ),
                ),
            ],
            options={
                "ordering": ["-uploaded_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="profileresume",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("profile",),
                name="uniq_active_resume_per_profile",
            ),
        ),
        migrations.AddIndex(
            model_name="profileresume",
            index=models.Index(fields=["profile", "is_active", "-uploaded_at"], name="profile_resume_active_idx"),
        ),
    ]
