from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0037_alter_sourceopportunite_type_source"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opportunite",
            name="statut",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Active"),
                    ("PENDING_REVIEW", "Pending review"),
                    ("EXPIREE", "Expirée"),
                    ("ARCHIVEE", "Archivée"),
                ],
                default="ACTIVE",
                max_length=20,
            ),
        ),
    ]
