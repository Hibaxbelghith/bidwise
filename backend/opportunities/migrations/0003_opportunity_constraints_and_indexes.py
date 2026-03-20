# Generated manually for Sprint 2 updates.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0002_initial"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="opportunite",
            name="opportuniti_type_op_985615_idx",
        ),
        migrations.AddConstraint(
            model_name="opportunite",
            constraint=models.UniqueConstraint(
                fields=("titre", "source", "date_publication"),
                name="uniq_opp_title_source_pub",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(
                fields=["type_opportunite", "statut"],
                name="opp_type_statut_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(fields=["statut"], name="opp_statut_idx"),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(fields=["date_publication"], name="opp_date_pub_idx"),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(fields=["date_limite"], name="opp_date_limite_idx"),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(fields=["date_creation"], name="opp_date_creation_idx"),
        ),
        migrations.AddIndex(
            model_name="opportunite",
            index=models.Index(
                fields=["statut", "date_publication"],
                name="opp_statut_date_pub_idx",
            ),
        ),
    ]
