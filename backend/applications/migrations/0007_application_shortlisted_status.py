from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0006_external_application_statuses"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidature",
            name="statut",
            field=models.CharField(
                choices=[
                    ("VUE", "Vue"),
                    ("INTERESSEE", "IntÃ©ressÃ©e"),
                    ("POSTULEE_EXTERNEMENT", "PostulÃ©e (site externe)"),
                    ("ABANDONNEE", "AbandonnÃ©e"),
                    ("SUBMITTED", "Submitted"),
                    ("VIEWED_BY_ORGANIZATION", "Viewed by organization"),
                    ("SHORTLISTED", "Shortlisted"),
                    ("REJECTED", "Rejected"),
                    ("WITHDRAWN", "Withdrawn"),
                    ("EXTERNAL_CLICKED", "External application opened"),
                    ("EXTERNAL_APPLIED_CONFIRMED", "External application confirmed"),
                    ("EXTERNAL_REMIND_LATER", "External reminder requested"),
                ],
                default="VUE",
                max_length=30,
            ),
        ),
    ]
