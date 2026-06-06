from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0038_alter_opportunite_statut_pending_review"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opportunite",
            name="statut",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Active"),
                    ("PENDING_REVIEW", "Pending review"),
                    ("REJECTED", "Rejected"),
                    ("EXPIREE", "Expirée"),
                    ("ARCHIVEE", "Archivée"),
                ],
                default="ACTIVE",
                max_length=20,
            ),
        ),
    ]
