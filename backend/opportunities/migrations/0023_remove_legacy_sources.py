from django.db import migrations
from django.db.models import Q


REMOVED_SOURCE_NAMES = (
    "HiInterns",
    "TunsieTenders",
    "TunisieTenders",
    "TunisieTravail",
)

REMOVED_SOURCE_KEYS = tuple(name.lower() for name in REMOVED_SOURCE_NAMES)


def _build_iexact_q(field_name, values):
    query = Q()
    for value in values:
        query |= Q(**{f"{field_name}__iexact": value})
    return query


def remove_legacy_sources(apps, schema_editor):
    SourceOpportunite = apps.get_model("opportunities", "SourceOpportunite")
    PipelineRun = apps.get_model("opportunities", "PipelineRun")

    SourceOpportunite.objects.filter(
        _build_iexact_q("nom", REMOVED_SOURCE_NAMES)
    ).delete()

    PipelineRun.objects.filter(
        _build_iexact_q("source", REMOVED_SOURCE_NAMES + REMOVED_SOURCE_KEYS)
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0022_pipelinerun_metrics"),
    ]

    operations = [
        migrations.RunPython(remove_legacy_sources, migrations.RunPython.noop),
    ]

