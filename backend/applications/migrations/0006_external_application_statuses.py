from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0005_application_contact_and_cover_letter_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="candidature",
            name="statut",
            field=models.CharField(
                choices=[
                    ("VUE", "Vue"),
                    ("INTERESSEE", "Intéressée"),
                    ("POSTULEE_EXTERNEMENT", "Postulée (site externe)"),
                    ("ABANDONNEE", "Abandonnée"),
                    ("SUBMITTED", "Submitted"),
                    ("VIEWED_BY_ORGANIZATION", "Viewed by organization"),
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
