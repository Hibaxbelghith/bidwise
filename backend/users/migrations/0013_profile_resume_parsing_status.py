from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_profile_embedding_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="profileresume",
            name="parsed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when resume parsing last completed",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="parsing_error",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Safe user-neutral parsing error detail for operators",
            ),
        ),
        migrations.AddField(
            model_name="profileresume",
            name="parsing_status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("PROCESSING", "Processing"),
                    ("SUCCEEDED", "Succeeded"),
                    ("EMPTY", "Empty"),
                    ("FAILED", "Failed"),
                    ("UNSUPPORTED", "Unsupported"),
                ],
                db_index=True,
                default="PENDING",
                help_text="Asynchronous resume parsing lifecycle status",
                max_length=20,
            ),
        ),
    ]
