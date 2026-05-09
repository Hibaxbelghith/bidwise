# Generated manually for normalized industry autocomplete hardening.

import django.contrib.postgres.indexes
from django.db import migrations, models


def backfill_normalized_industries(apps, schema_editor):
    from opportunities.normalization.industries import normalize_industries

    Opportunite = apps.get_model("opportunities", "Opportunite")
    pending = []
    for opportunity in (
        Opportunite.objects
        .only("id", "extra_data", "normalized_industries")
        .order_by("id")
        .iterator(chunk_size=500)
    ):
        extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
        industries = normalize_industries(extra_data.get("company_sector"))
        if not industries:
            continue
        opportunity.normalized_industries = industries
        pending.append(opportunity)
        if len(pending) >= 500:
            Opportunite.objects.bulk_update(pending, ["normalized_industries"], batch_size=500)
            pending.clear()
    if pending:
        Opportunite.objects.bulk_update(pending, ["normalized_industries"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0028_profilesuggestion_serving_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="normalized_industries",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical industry/interest sectors derived from source company sector metadata",
            ),
        ),
        migrations.AlterField(
            model_name="profilesuggestion",
            name="term_type",
            field=models.CharField(
                choices=[
                    ("SKILL", "Skill"),
                    ("ROLE", "Role"),
                    ("INTEREST", "Interest"),
                ],
                db_index=True,
                max_length=16,
            ),
        ),
        migrations.RunPython(backfill_normalized_industries, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="opportunite",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["normalized_industries"],
                name="opp_norm_industries_gin",
            ),
        ),
    ]
