from django.db import migrations


def mark_admin_rejected_opportunities(apps, schema_editor):
    Opportunite = apps.get_model("opportunities", "Opportunite")
    queryset = Opportunite.objects.filter(
        statut="ARCHIVEE",
        extra_data__published_by="organization",
        extra_data__moderation__admin_decision__action="rejected",
    )
    queryset.update(statut="REJECTED")


def reverse_mark_admin_rejected_opportunities(apps, schema_editor):
    Opportunite = apps.get_model("opportunities", "Opportunite")
    queryset = Opportunite.objects.filter(
        statut="REJECTED",
        extra_data__published_by="organization",
        extra_data__moderation__admin_decision__action="rejected",
    )
    queryset.update(statut="ARCHIVEE")


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0039_alter_opportunite_statut_rejected"),
    ]

    operations = [
        migrations.RunPython(mark_admin_rejected_opportunities, reverse_mark_admin_rejected_opportunities),
    ]
