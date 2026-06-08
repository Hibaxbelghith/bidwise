from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0040_rejected_admin_decisions_status"),
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
                    ("SUSPENDUE", "Suspended"),
                    ("FERMEE", "Closed"),
                    ("EXPIREE", "Expirée"),
                    ("ARCHIVEE", "Archivée"),
                ],
                default="ACTIVE",
                max_length=20,
            ),
        ),
    ]
