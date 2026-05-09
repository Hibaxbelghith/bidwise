import re
import unicodedata

from django.db import migrations, models


CONTRACT_TYPE_CDI = "CDI"
CONTRACT_TYPE_CDD = "CDD"
CONTRACT_TYPE_INTERNSHIP = "INTERNSHIP"
CONTRACT_TYPE_SIVP = "SIVP"
CONTRACT_TYPE_FREELANCE = "FREELANCE"
CONTRACT_TYPE_ALTERNANCE = "ALTERNANCE"
CONTRACT_TYPE_TEMPORARY_INTERIM = "TEMPORARY_INTERIM"
CONTRACT_TYPE_SEASONAL = "SEASONAL"
CONTRACT_TYPE_PUBLIC_SECTOR = "PUBLIC_SECTOR"

CANONICAL_CONTRACT_TYPES = {
    CONTRACT_TYPE_CDI,
    CONTRACT_TYPE_CDD,
    CONTRACT_TYPE_INTERNSHIP,
    CONTRACT_TYPE_SIVP,
    CONTRACT_TYPE_FREELANCE,
    CONTRACT_TYPE_ALTERNANCE,
    CONTRACT_TYPE_TEMPORARY_INTERIM,
    CONTRACT_TYPE_SEASONAL,
    CONTRACT_TYPE_PUBLIC_SECTOR,
}

WORK_MODE_REMOTE = "REMOTE"
WORK_MODE_HYBRID = "HYBRID"
WORK_MODE_ON_SITE = "ON_SITE"
WORK_MODE_UNSPECIFIED = "UNSPECIFIED"

CONTRACT_TYPE_ALIASES = {
    "cdi": CONTRACT_TYPE_CDI,
    "contrat a duree indeterminee": CONTRACT_TYPE_CDI,
    "contrat duree indeterminee": CONTRACT_TYPE_CDI,
    "permanent": CONTRACT_TYPE_CDI,
    "permanent contract": CONTRACT_TYPE_CDI,
    "cdd": CONTRACT_TYPE_CDD,
    "contrat a duree determinee": CONTRACT_TYPE_CDD,
    "contrat duree determinee": CONTRACT_TYPE_CDD,
    "fixed term": CONTRACT_TYPE_CDD,
    "fixed term contract": CONTRACT_TYPE_CDD,
    "contract": CONTRACT_TYPE_CDD,
    "contractuel": CONTRACT_TYPE_CDD,
    "stage": CONTRACT_TYPE_INTERNSHIP,
    "stage pfe": CONTRACT_TYPE_INTERNSHIP,
    "pfe": CONTRACT_TYPE_INTERNSHIP,
    "projet fin d etudes": CONTRACT_TYPE_INTERNSHIP,
    "projet de fin d etudes": CONTRACT_TYPE_INTERNSHIP,
    "internship": CONTRACT_TYPE_INTERNSHIP,
    "intern": CONTRACT_TYPE_INTERNSHIP,
    "stagiaire": CONTRACT_TYPE_INTERNSHIP,
    "trainee": CONTRACT_TYPE_INTERNSHIP,
    "تربص": CONTRACT_TYPE_INTERNSHIP,
    "sivp": CONTRACT_TYPE_SIVP,
    "contrat sivp": CONTRACT_TYPE_SIVP,
    "freelance": CONTRACT_TYPE_FREELANCE,
    "independant": CONTRACT_TYPE_FREELANCE,
    "independent": CONTRACT_TYPE_FREELANCE,
    "independant freelance": CONTRACT_TYPE_FREELANCE,
    "independent freelance": CONTRACT_TYPE_FREELANCE,
    "consultant": CONTRACT_TYPE_FREELANCE,
    "self employed": CONTRACT_TYPE_FREELANCE,
    "عمل حر": CONTRACT_TYPE_FREELANCE,
    "alternance": CONTRACT_TYPE_ALTERNANCE,
    "apprentissage": CONTRACT_TYPE_ALTERNANCE,
    "apprenticeship": CONTRACT_TYPE_ALTERNANCE,
    "interim": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "intérim": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "temporary": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "temporaire": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "travail temporaire": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "saisonnier": CONTRACT_TYPE_SEASONAL,
    "seasonal": CONTRACT_TYPE_SEASONAL,
    "travail saisonnier": CONTRACT_TYPE_SEASONAL,
    "statutaire": CONTRACT_TYPE_PUBLIC_SECTOR,
    "fonction publique": CONTRACT_TYPE_PUBLIC_SECTOR,
    "public sector": CONTRACT_TYPE_PUBLIC_SECTOR,
}

WORK_MODE_ALIASES = {
    "remote": WORK_MODE_REMOTE,
    "full remote": WORK_MODE_REMOTE,
    "a distance": WORK_MODE_REMOTE,
    "teletravail": WORK_MODE_REMOTE,
    "tele travail": WORK_MODE_REMOTE,
    "work from home": WORK_MODE_REMOTE,
    "home office": WORK_MODE_REMOTE,
    "oui": WORK_MODE_REMOTE,
    "yes": WORK_MODE_REMOTE,
    "عن بعد": WORK_MODE_REMOTE,
    "عمل عن بعد": WORK_MODE_REMOTE,
    "hybride": WORK_MODE_HYBRID,
    "hybrid": WORK_MODE_HYBRID,
    "mixte": WORK_MODE_HYBRID,
    "هجين": WORK_MODE_HYBRID,
    "presentiel": WORK_MODE_ON_SITE,
    "sur site": WORK_MODE_ON_SITE,
    "on site": WORK_MODE_ON_SITE,
    "onsite": WORK_MODE_ON_SITE,
    "office": WORK_MODE_ON_SITE,
    "non": WORK_MODE_ON_SITE,
    "no": WORK_MODE_ON_SITE,
    "حضوري": WORK_MODE_ON_SITE,
}

SCHEDULE_ALIASES = {
    "plein temps",
    "temps plein",
    "full time",
    "fulltime",
    "full",
    "دوام كامل",
    "mi temps",
    "temps partiel",
    "part time",
    "parttime",
    "partiel",
    "دوام جزئي",
}

_SPLIT_RE = re.compile(r"\s*(?:[-–—/,;|+&]|\bet\b|\bou\b|\bor\b)\s*", re.IGNORECASE)


def normalize_key(value):
    if value is None:
        return ""

    text = str(value).replace("\xa0", " ").strip()
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = text.replace("_", " ")
    text = re.sub(r"[’'`]", " ", text)
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def clean_display_value(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip(" \t\r\n,;|/-")


def coerce_items(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            items.extend(coerce_items(item))
        return items
    return [value]


def split_contract_values(value):
    tokens = []
    for item in coerce_items(value):
        text = clean_display_value(item)
        if not text:
            continue
        for part in _SPLIT_RE.split(text):
            cleaned = clean_display_value(part)
            if cleaned:
                tokens.append(cleaned)
    return tokens


def append_unique(values, value):
    if value and value not in values:
        values.append(value)


def normalize_contract_types(value):
    canonical = []
    for token in split_contract_values(value):
        key = normalize_key(token)
        if not key:
            continue

        upper_text = clean_display_value(token).upper()
        if upper_text in CANONICAL_CONTRACT_TYPES:
            append_unique(canonical, upper_text)
            continue

        mapped = CONTRACT_TYPE_ALIASES.get(key)
        if mapped:
            append_unique(canonical, mapped)
            continue

        if key in WORK_MODE_ALIASES or key in SCHEDULE_ALIASES:
            continue

    return canonical


def normalize_work_mode_preference(value):
    if value is None:
        return None

    text = clean_display_value(value)
    if not text:
        return None

    upper_text = text.upper()
    if upper_text in {WORK_MODE_REMOTE, WORK_MODE_HYBRID, WORK_MODE_ON_SITE}:
        return upper_text

    key = normalize_key(text)
    mapped = WORK_MODE_ALIASES.get(key)
    if mapped:
        return mapped

    for alias, canonical in WORK_MODE_ALIASES.items():
        if len(alias) >= 4 and alias in key:
            return canonical

    return WORK_MODE_UNSPECIFIED


def normalize_work_mode_list(value):
    cleaned = []
    for item in coerce_items(value):
        canonical = normalize_work_mode_preference(item)
        if not canonical or canonical == WORK_MODE_UNSPECIFIED:
            continue
        append_unique(cleaned, canonical)
    return cleaned


def forwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "employment_types",
        "remote_preference",
        "work_mode_preferences",
    )

    for profil in queryset.iterator(chunk_size=500):
        profil.employment_types = normalize_contract_types(profil.employment_types)

        modes = normalize_work_mode_list(profil.work_mode_preferences)
        if not modes:
            modes = normalize_work_mode_list(profil.remote_preference)
        profil.work_mode_preferences = modes
        profil.remote_preference = modes[0] if modes else None
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(
                batch,
                ["employment_types", "remote_preference", "work_mode_preferences"],
                batch_size=500,
            )
            batch = []

    if batch:
        Profil.objects.bulk_update(
            batch,
            ["employment_types", "remote_preference", "work_mode_preferences"],
            batch_size=500,
        )


def backwards(apps, schema_editor):
    Profil = apps.get_model("users", "Profil")
    batch = []
    queryset = Profil.objects.all().only(
        "id",
        "remote_preference",
        "work_mode_preferences",
    )

    for profil in queryset.iterator(chunk_size=500):
        modes = normalize_work_mode_list(profil.work_mode_preferences)
        profil.remote_preference = modes[0] if modes else None
        batch.append(profil)

        if len(batch) >= 500:
            Profil.objects.bulk_update(batch, ["remote_preference"], batch_size=500)
            batch = []

    if batch:
        Profil.objects.bulk_update(batch, ["remote_preference"], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_profil_preferred_locations"),
    ]

    operations = [
        migrations.AddField(
            model_name="profil",
            name="work_mode_preferences",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical desired work modes, e.g. ['REMOTE','HYBRID']",
            ),
        ),
        migrations.AlterField(
            model_name="profil",
            name="remote_preference",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ON_SITE", "On-site"),
                    ("REMOTE", "Remote"),
                    ("HYBRID", "Hybrid"),
                ],
                help_text="Legacy single remote work preference",
                max_length=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="profil",
            name="employment_types",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical desired contract/employment types",
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
