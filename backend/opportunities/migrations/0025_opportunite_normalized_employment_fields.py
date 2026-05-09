import re
import unicodedata

from django.db import migrations, models


WORK_MODE_UNSPECIFIED = "UNSPECIFIED"
SCHEDULE_UNSPECIFIED = "UNSPECIFIED"

CONTRACT_ALIASES = {
    "cdi": "CDI",
    "contrat a duree indeterminee": "CDI",
    "permanent": "CDI",
    "cdd": "CDD",
    "contrat a duree determinee": "CDD",
    "fixed term": "CDD",
    "contract": "CDD",
    "contractuel": "CDD",
    "stage": "INTERNSHIP",
    "stage pfe": "INTERNSHIP",
    "pfe": "INTERNSHIP",
    "projet fin d etudes": "INTERNSHIP",
    "internship": "INTERNSHIP",
    "intern": "INTERNSHIP",
    "stagiaire": "INTERNSHIP",
    "trainee": "INTERNSHIP",
    "تربص": "INTERNSHIP",
    "sivp": "SIVP",
    "contrat sivp": "SIVP",
    "freelance": "FREELANCE",
    "independant": "FREELANCE",
    "independent": "FREELANCE",
    "independant freelance": "FREELANCE",
    "consultant": "FREELANCE",
    "عمل حر": "FREELANCE",
    "alternance": "ALTERNANCE",
    "apprentissage": "ALTERNANCE",
    "apprenticeship": "ALTERNANCE",
    "interim": "TEMPORARY_INTERIM",
    "intérim": "TEMPORARY_INTERIM",
    "temporary": "TEMPORARY_INTERIM",
    "temporaire": "TEMPORARY_INTERIM",
    "saisonnier": "SEASONAL",
    "seasonal": "SEASONAL",
    "statutaire": "PUBLIC_SECTOR",
    "fonction publique": "PUBLIC_SECTOR",
    "public sector": "PUBLIC_SECTOR",
}

WORK_MODE_ALIASES = {
    "remote": "REMOTE",
    "full remote": "REMOTE",
    "a distance": "REMOTE",
    "teletravail": "REMOTE",
    "work from home": "REMOTE",
    "home office": "REMOTE",
    "oui": "REMOTE",
    "yes": "REMOTE",
    "عن بعد": "REMOTE",
    "عمل عن بعد": "REMOTE",
    "hybride": "HYBRID",
    "hybrid": "HYBRID",
    "mixte": "HYBRID",
    "هجين": "HYBRID",
    "presentiel": "ON_SITE",
    "sur site": "ON_SITE",
    "on site": "ON_SITE",
    "onsite": "ON_SITE",
    "non": "ON_SITE",
    "no": "ON_SITE",
    "حضوري": "ON_SITE",
}

SCHEDULE_ALIASES = {
    "plein temps": "FULL_TIME",
    "temps plein": "FULL_TIME",
    "full time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "دوام كامل": "FULL_TIME",
    "mi temps": "PART_TIME",
    "temps partiel": "PART_TIME",
    "part time": "PART_TIME",
    "parttime": "PART_TIME",
    "partiel": "PART_TIME",
    "دوام جزئي": "PART_TIME",
}

SPLIT_RE = re.compile(r"\s*(?:[-–—/,;|+&]|\bet\b|\bou\b|\bor\b)\s*", re.IGNORECASE)


def normalize_key(value):
    if value is None:
        return ""

    text = str(value).replace("\xa0", " ").strip()
    if not text:
        return ""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[’'`]", " ", text)
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


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
        text = str(item or "").replace("\xa0", " ").strip(" \t\r\n,;|/-")
        if not text:
            continue
        for part in SPLIT_RE.split(text):
            cleaned = str(part or "").strip(" \t\r\n,;|/-")
            if cleaned:
                tokens.append(cleaned)
    return tokens


def normalize_contract_types(value):
    normalized = []
    for token in split_contract_values(value):
        mapped = CONTRACT_ALIASES.get(normalize_key(token))
        if mapped and mapped not in normalized:
            normalized.append(mapped)
    return normalized


def normalize_work_mode(value):
    for item in coerce_items(value):
        key = normalize_key(item)
        if not key:
            continue
        mapped = WORK_MODE_ALIASES.get(key)
        if mapped:
            return mapped
        for alias, canonical in WORK_MODE_ALIASES.items():
            if len(alias) >= 4 and alias in key:
                return canonical
    return WORK_MODE_UNSPECIFIED


def normalize_schedule(value):
    for item in coerce_items(value):
        key = normalize_key(item)
        if not key:
            continue
        mapped = SCHEDULE_ALIASES.get(key)
        if mapped:
            return mapped
        for alias in ("temps partiel", "mi temps", "part time", "parttime", "partiel"):
            if alias in key:
                return "PART_TIME"
        for alias in ("plein temps", "temps plein", "full time", "fulltime"):
            if alias in key:
                return "FULL_TIME"
    return SCHEDULE_UNSPECIFIED


def forwards(apps, schema_editor):
    Opportunite = apps.get_model("opportunities", "Opportunite")
    RawOpportunite = apps.get_model("opportunities", "RawOpportunite")

    raw_remote_by_opportunity_id = {}
    raw_rows = RawOpportunite.objects.exclude(canonical_id=None).values_list(
        "canonical_id",
        "raw_payload",
    )
    for canonical_id, payload in raw_rows.iterator(chunk_size=1000):
        if canonical_id in raw_remote_by_opportunity_id:
            continue
        if isinstance(payload, dict):
            remote = payload.get("remote")
            if remote not in (None, ""):
                raw_remote_by_opportunity_id[canonical_id] = remote

    batch = []
    queryset = Opportunite.objects.all().only(
        "id",
        "contract_type",
        "availability",
        "extra_data",
        "normalized_contract_types",
        "normalized_work_mode",
        "normalized_schedule",
    )

    for opportunity in queryset.iterator(chunk_size=500):
        extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
        parsed_contract_types = extra_data.get("contract_types")
        remote = raw_remote_by_opportunity_id.get(opportunity.id)

        opportunity.normalized_contract_types = normalize_contract_types(
            [
                opportunity.contract_type,
                parsed_contract_types,
            ]
        )
        opportunity.normalized_work_mode = normalize_work_mode(
            [
                remote,
                opportunity.availability,
                opportunity.contract_type,
            ]
        )
        opportunity.normalized_schedule = normalize_schedule(
            [
                opportunity.availability,
                opportunity.contract_type,
            ]
        )
        batch.append(opportunity)

        if len(batch) >= 500:
            Opportunite.objects.bulk_update(
                batch,
                [
                    "normalized_contract_types",
                    "normalized_work_mode",
                    "normalized_schedule",
                ],
                batch_size=500,
            )
            batch = []

    if batch:
        Opportunite.objects.bulk_update(
            batch,
            [
                "normalized_contract_types",
                "normalized_work_mode",
                "normalized_schedule",
            ],
            batch_size=500,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("opportunities", "0024_sourceschedulerstate"),
    ]

    operations = [
        migrations.AddField(
            model_name="opportunite",
            name="normalized_contract_types",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Canonical contract/employment types derived from raw source values",
            ),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="normalized_work_mode",
            field=models.CharField(
                blank=True,
                default="UNSPECIFIED",
                help_text="Canonical work mode derived from raw availability/remote values",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="opportunite",
            name="normalized_schedule",
            field=models.CharField(
                blank=True,
                default="UNSPECIFIED",
                help_text="Canonical schedule derived from raw availability/contract values",
                max_length=20,
            ),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
