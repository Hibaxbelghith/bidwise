import applications.models
import django.db.models.deletion
import users.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applications", "0002_initial"),
        ("users", "0025_alter_auditlog_action_org_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidature",
            name="cover_letter",
            field=models.FileField(
                blank=True,
                null=True,
                storage=users.storage.ProfileResumeStorage(),
                upload_to=applications.models.application_cover_letter_upload_to,
            ),
        ),
        migrations.AddField(
            model_name="candidature",
            name="cv",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="users.profileresume",
            ),
        ),
        migrations.AddField(
            model_name="candidature",
            name="submitted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
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
                ],
                default="VUE",
                max_length=30,
            ),
        ),
    ]
