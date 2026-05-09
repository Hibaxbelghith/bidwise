import re
import unicodedata

from django.db import migrations, models


TUNISIAN_LOCATIONS = (
    "Tunis",
    "Sidi Bouzid",
    "Sfax",
    "Sousse",
    "Kairouan",
    "Métouia",
    "Kebili",
    "Sukrah",
    "Gabès",
    "Ariana",
    "Sakiet ed Daier",
    "Gafsa",
    "Msaken",
    "Medenine",
    "Béja",
    "Kasserine",
    "Radès",
    "Hammamet",
    "Tataouine",
    "Monastir",
    "La Marsa",
    "Ben Arous",
    "Sakiet ez Zit",
    "Zarzis",
    "Ben Gardane",
    "Mahdia",
    "Houmt Souk",
    "Fouchana",
    "Le Kram",
    "El Kef",
    "El Hamma",
    "Nabeul",
    "Le Bardo",
    "Djemmal",
    "Korba",
    "Menzel Temime",
    "Ghardimaou",
    "Midoun",
    "Menzel Bourguiba",
    "Manouba",
    "Kélibia",
    "Rass el Djebel",
    "Oued Lill",
    "Moknine",
    "Bir Ali Ben Khalifa",
    "Kelaa Kebira",
    "El Jem",
    "Tebourba",
    "Ksar Hellal",
    "Douz",
    "Bizerte",
    "Jendouba",
    "La Goulette",
    "Jedeïda",
    "Soliman",
    "Hammam Sousse",
    "Sbiba",
    "Tabarka",
    "Sejenane",
    "Metlaoui",
    "Hammam-Lif",
    "Teboulba",
    "Tozeur",
    "Beni Khiar",
    "Dar Chabanne",
    "Aïne Draham",
    "Bou Salem",
    "Ez Zahra",
    "Kalaa Srira",
    "Skhira",
    "Akouda",
    "El Ksar",
    "Mateur",
    "Siliana",
    "Rhennouch",
    "Dahmani",
    "El Alia",
    "Ar Rudayyif",
    "Zaghouan",
)


def _collapse_location_spacing(value):
    text = re.sub(r"\s+", " ", value.strip())
    return re.sub(r"\s*-\s*", "-", text)


def _strip_accents(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _location_lookup_key(value):
    text = _strip_accents(_collapse_location_spacing(value))
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


TUNISIAN_LOCATION_BY_KEY = {
    _location_lookup_key(location): location
    for location in TUNISIAN_LOCATIONS
}


def _normalize_location(value):
    if value is None:
        return ""

    text = _collapse_location_spacing(str(value))
    if not text:
        return ""

    return TUNISIAN_LOCATION_BY_KEY.get(_location_lookup_key(text), text)


def _clean_locations(value):
    if value is None:
        raw_items = []
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = [value]

    cleaned = []
    seen = set()
    for item in raw_items:
        text = _normalize_location(item)
        if not text:
            continue

        key = _location_lookup_key(text)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def forwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "preferred_location",
        "preferred_locations",
    )

    for profil in queryset.iterator(chunk_size=500):
        profil.preferred_locations = _clean_locations(profil.preferred_location)
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(
                batch,
                ["preferred_locations"],
                batch_size=500,
            )
            batch = []

    if batch:
        Profil.objects.bulk_update(
            batch,
            ["preferred_locations"],
            batch_size=500,
        )


def backwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "preferred_location",
        "preferred_locations",
    )

    for profil in queryset.iterator(chunk_size=500):
        locations = _clean_locations(profil.preferred_locations)
        profil.preferred_location = ", ".join(locations)[:255] or None
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(
                batch,
                ["preferred_location"],
                batch_size=500,
            )
            batch = []

    if batch:
        Profil.objects.bulk_update(
            batch,
            ["preferred_location"],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_profil_embedding_features_hash"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="preferred_locations",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Preferred Tunisian cities/regions and custom locations",
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(
            model_name="profil",
            name="preferred_location",
        ),
    ]
