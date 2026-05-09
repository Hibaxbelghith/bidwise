from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_profile_resume_parsing_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileresume",
            name="extracted_skills",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical semantic skills extracted from the resume. Does not overwrite user-entered skills.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="extracted_domains",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical semantic domains inferred from the resume.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="extracted_tools",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical tools and platforms extracted from the resume.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="extracted_languages",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Languages detected in the parsed resume text.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_version",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Version of the semantic resume enrichment pipeline.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_content_hash",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Content hash used to skip repeated semantic CV inference.",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_updated_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Last time semantic resume enrichment completed.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_confidence",
            field=models.FloatField(
                default=0.0,
                help_text="Confidence score for extracted semantic resume signals.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_status",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="PENDING",
                help_text="Lifecycle status for semantic resume enrichment.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_error",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Safe operator-facing semantic enrichment error.",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="semantic_resume_metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Diagnostic metadata for semantic resume enrichment.",
            ),
        ),
    ]

