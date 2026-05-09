from django.db import migrations, models


def _clean_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, (list, tuple)):
        raw_items = value
    else:
        raw_items = [value]

    cleaned = []
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        cleaned.append(text)
    return cleaned


def forwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "competences",
        "domaines_interet",
        "competences_json",
        "domaines_interet_json",
    )

    for profil in queryset.iterator(chunk_size=500):
        profil.competences_json = _clean_list(profil.competences)
        profil.domaines_interet_json = _clean_list(profil.domaines_interet)
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(
                batch,
                ["competences_json", "domaines_interet_json"],
                batch_size=500,
            )
            batch = []

    if batch:
        Profil.objects.bulk_update(
            batch,
            ["competences_json", "domaines_interet_json"],
            batch_size=500,
        )


def backwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "competences",
        "domaines_interet",
        "competences_json",
        "domaines_interet_json",
    )

    for profil in queryset.iterator(chunk_size=500):
        profil.competences = ", ".join(_clean_list(profil.competences_json))
        profil.domaines_interet = ", ".join(_clean_list(profil.domaines_interet_json))
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(
                batch,
                ["competences", "domaines_interet"],
                batch_size=500,
            )
            batch = []

    if batch:
        Profil.objects.bulk_update(
            batch,
            ["competences", "domaines_interet"],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_utilisateur_is_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="competences_json",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="profil",
            name="domaines_interet_json",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="profil",
            name="embedding",
            field=models.JSONField(
                blank=True,
                help_text="Cached user embedding generated from normalized profile features",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="profil",
            name="last_embedding_update",
            field=models.DateTimeField(
                blank=True,
                help_text="Last time the cached profile embedding was generated",
                null=True,
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="profil",
            name="competences",
        ),
        migrations.RemoveField(
            model_name="profil",
            name="domaines_interet",
        ),
        migrations.RenameField(
            model_name="profil",
            old_name="competences_json",
            new_name="competences",
        ),
        migrations.RenameField(
            model_name="profil",
            old_name="domaines_interet_json",
            new_name="domaines_interet",
        ),
        migrations.AlterField(
            model_name="profil",
            name="competences",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Structured list of profile skills used for ML features",
            ),
        ),
        migrations.AlterField(
            model_name="profil",
            name="domaines_interet",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Structured list of interest domains used for recommendations",
            ),
        ),
    ]
