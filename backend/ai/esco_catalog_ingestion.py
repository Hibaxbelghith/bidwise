from __future__ import annotations

import csv
import logging
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction

from ai.models import ESCOOccupationCatalog, ESCOOccupationSkillRelation, ESCOSkill


logger = logging.getLogger(__name__)


CSV_ENCODING = "utf-8-sig"
CSV_DELIMITER = ","


@dataclass
class IngestionStats:
    skill_rows_read: int = 0
    occupation_rows_read: int = 0
    relation_rows_read: int = 0
    skipped_rows: int = 0
    duplicate_relation_rows: int = 0
    missing_relation_targets: int = 0
    malformed_files: list[str] = field(default_factory=list)
    skill_creates: int = 0
    skill_updates: int = 0
    occupation_creates: int = 0
    occupation_updates: int = 0
    relation_creates: int = 0
    relation_existing: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "skill_rows_read": self.skill_rows_read,
            "occupation_rows_read": self.occupation_rows_read,
            "relation_rows_read": self.relation_rows_read,
            "skipped_rows": self.skipped_rows,
            "duplicate_relation_rows": self.duplicate_relation_rows,
            "missing_relation_targets": self.missing_relation_targets,
            "malformed_files": list(self.malformed_files),
            "skill_creates": self.skill_creates,
            "skill_updates": self.skill_updates,
            "occupation_creates": self.occupation_creates,
            "occupation_updates": self.occupation_updates,
            "relation_creates": self.relation_creates,
            "relation_existing": self.relation_existing,
        }


def _clean_text(value) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = text.replace("\x00", " ").replace("\ufeff", " ")
    text = " ".join(text.split())
    return text.strip()


def _split_multivalue(value) -> list[str]:
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    pieces = []
    for chunk in raw.split("\n"):
        candidate = _clean_text(chunk)
        if candidate:
            pieces.append(candidate)
    return _dedupe_list(pieces)


def _dedupe_list(values) -> list[str]:
    seen = set()
    output = []
    for value in values:
        text = _clean_text(value)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _build_search_text(*value_groups) -> str:
    flattened = []
    for group in value_groups:
        if isinstance(group, (list, tuple)):
            flattened.extend(group)
        else:
            flattened.append(group)
    return " | ".join(_dedupe_list(flattened))


def _read_csv_rows(path: Path, stats: IngestionStats):
    if not path.exists():
        logger.warning("ESCO ingestion skipped missing file path=%s", path)
        stats.malformed_files.append(str(path))
        return [], []

    try:
        with open(path, "r", encoding=CSV_ENCODING, errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=CSV_DELIMITER)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, csv.Error) as exc:
        logger.warning("ESCO ingestion failed to read csv path=%s error=%s", path, exc)
        stats.malformed_files.append(str(path))
        return [], []

    return fieldnames, rows


def _merge_skill_language_rows(
    rows: list[dict[str, str]],
    language: str,
    merged: dict[str, dict[str, object]],
    stats: IngestionStats,
) -> None:
    uri_field = "conceptUri"
    label_field = "preferredLabel"

    for row in rows:
        stats.skill_rows_read += 1
        uri = _clean_text(row.get(uri_field))
        if not uri:
            stats.skipped_rows += 1
            continue

        merged_row = merged.setdefault(
            uri,
            {
                "uri": uri,
                "preferred_label_en": "",
                "preferred_label_fr": "",
                "alt_labels_en": [],
                "alt_labels_fr": [],
                "hidden_labels_en": [],
                "hidden_labels_fr": [],
            },
        )

        preferred_label = _clean_text(row.get(label_field))
        alt_labels = _split_multivalue(row.get("altLabels"))
        hidden_labels = _split_multivalue(row.get("hiddenLabels"))

        merged_row[f"preferred_label_{language}"] = (
            merged_row.get(f"preferred_label_{language}") or preferred_label
        )
        merged_row[f"alt_labels_{language}"] = _dedupe_list(
            [*list(merged_row.get(f"alt_labels_{language}", [])), *alt_labels]
        )
        merged_row[f"hidden_labels_{language}"] = _dedupe_list(
            [*list(merged_row.get(f"hidden_labels_{language}", [])), *hidden_labels]
        )


def _merge_occupation_language_rows(
    rows: list[dict[str, str]],
    language: str,
    merged: dict[str, dict[str, object]],
    stats: IngestionStats,
) -> None:
    uri_field = "conceptUri"
    label_field = "preferredLabel"

    for row in rows:
        stats.occupation_rows_read += 1
        uri = _clean_text(row.get(uri_field))
        if not uri:
            stats.skipped_rows += 1
            continue

        merged_row = merged.setdefault(
            uri,
            {
                "uri": uri,
                "preferred_label_en": "",
                "preferred_label_fr": "",
                "alt_labels_en": [],
                "alt_labels_fr": [],
                "hidden_labels_en": [],
                "hidden_labels_fr": [],
                "isco_group": "",
                "code": "",
                "nace_code": "",
            },
        )

        preferred_label = _clean_text(row.get(label_field))
        merged_row[f"preferred_label_{language}"] = (
            merged_row.get(f"preferred_label_{language}") or preferred_label
        )
        merged_row[f"alt_labels_{language}"] = _dedupe_list(
            [*list(merged_row.get(f"alt_labels_{language}", [])), *_split_multivalue(row.get("altLabels"))]
        )
        merged_row[f"hidden_labels_{language}"] = _dedupe_list(
            [*list(merged_row.get(f"hidden_labels_{language}", [])), *_split_multivalue(row.get("hiddenLabels"))]
        )
        merged_row["isco_group"] = merged_row.get("isco_group") or _clean_text(row.get("iscoGroup"))
        merged_row["code"] = merged_row.get("code") or _clean_text(row.get("code"))
        merged_row["nace_code"] = merged_row.get("nace_code") or _clean_text(row.get("naceCode"))


def _normalize_skill_payload(payload: dict[str, object]) -> dict[str, object]:
    preferred_label_en = _clean_text(payload.get("preferred_label_en"))
    preferred_label_fr = _clean_text(payload.get("preferred_label_fr"))
    alt_labels_en = _dedupe_list(payload.get("alt_labels_en", []))
    alt_labels_fr = _dedupe_list(payload.get("alt_labels_fr", []))
    hidden_labels_en = _dedupe_list(payload.get("hidden_labels_en", []))
    hidden_labels_fr = _dedupe_list(payload.get("hidden_labels_fr", []))
    preferred_label = preferred_label_en or preferred_label_fr or _clean_text(payload.get("uri"))
    alt_labels = _dedupe_list([*alt_labels_en, *alt_labels_fr, *hidden_labels_en, *hidden_labels_fr])
    search_text = _build_search_text(
        preferred_label_en,
        preferred_label_fr,
        alt_labels_en,
        alt_labels_fr,
        hidden_labels_en,
        hidden_labels_fr,
    )
    return {
        "uri": payload["uri"],
        "preferred_label": preferred_label,
        "alt_labels": alt_labels,
        "preferred_label_en": preferred_label_en,
        "preferred_label_fr": preferred_label_fr,
        "alt_labels_en": alt_labels_en,
        "alt_labels_fr": alt_labels_fr,
        "hidden_labels_en": hidden_labels_en,
        "hidden_labels_fr": hidden_labels_fr,
        "search_text_multilingual": search_text,
    }


def _normalize_occupation_payload(payload: dict[str, object]) -> dict[str, object]:
    preferred_label_en = _clean_text(payload.get("preferred_label_en"))
    preferred_label_fr = _clean_text(payload.get("preferred_label_fr"))
    alt_labels_en = _dedupe_list(payload.get("alt_labels_en", []))
    alt_labels_fr = _dedupe_list(payload.get("alt_labels_fr", []))
    hidden_labels_en = _dedupe_list(payload.get("hidden_labels_en", []))
    hidden_labels_fr = _dedupe_list(payload.get("hidden_labels_fr", []))
    return {
        "uri": payload["uri"],
        "preferred_label_en": preferred_label_en,
        "preferred_label_fr": preferred_label_fr,
        "alt_labels_en": alt_labels_en,
        "alt_labels_fr": alt_labels_fr,
        "hidden_labels_en": hidden_labels_en,
        "hidden_labels_fr": hidden_labels_fr,
        "search_text_multilingual": _build_search_text(
            preferred_label_en,
            preferred_label_fr,
            alt_labels_en,
            alt_labels_fr,
            hidden_labels_en,
            hidden_labels_fr,
        ),
        "isco_group": _clean_text(payload.get("isco_group")),
        "code": _clean_text(payload.get("code")),
        "nace_code": _clean_text(payload.get("nace_code")),
    }


def _collect_relation_keys(
    rows: list[dict[str, str]],
    stats: IngestionStats,
) -> set[tuple[str, str, str]]:
    keys = set()
    for row in rows:
        stats.relation_rows_read += 1
        occupation_uri = _clean_text(row.get("occupationUri"))
        skill_uri = _clean_text(row.get("skillUri"))
        relation_type = _clean_text(row.get("relationType"))
        if not occupation_uri or not skill_uri:
            stats.skipped_rows += 1
            continue
        key = (occupation_uri, skill_uri, relation_type)
        if key in keys:
            stats.duplicate_relation_rows += 1
            continue
        keys.add(key)
    return keys


def _update_changed_fields(instance, payload: dict[str, object], field_names: list[str]) -> list[str]:
    changed = []
    for field_name in field_names:
        new_value = payload[field_name]
        if getattr(instance, field_name) != new_value:
            setattr(instance, field_name, new_value)
            changed.append(field_name)
    return changed


def _upsert_skills(skill_payloads: list[dict[str, object]], stats: IngestionStats, batch_size: int) -> None:
    if not skill_payloads:
        return

    uri_list = [payload["uri"] for payload in skill_payloads]
    existing_map = {
        skill.uri: skill
        for skill in ESCOSkill.objects.filter(uri__in=uri_list)
    }
    create_rows = []
    update_rows = []
    update_fields = [
        "preferred_label",
        "alt_labels",
        "preferred_label_en",
        "preferred_label_fr",
        "alt_labels_en",
        "alt_labels_fr",
        "hidden_labels_en",
        "hidden_labels_fr",
        "search_text_multilingual",
    ]

    for payload in skill_payloads:
        current = existing_map.get(payload["uri"])
        if current is None:
            create_rows.append(ESCOSkill(**payload))
            continue
        changed_fields = _update_changed_fields(current, payload, update_fields)
        if changed_fields:
            update_rows.append(current)

    if create_rows:
        ESCOSkill.objects.bulk_create(create_rows, batch_size=batch_size)
        stats.skill_creates += len(create_rows)
    if update_rows:
        ESCOSkill.objects.bulk_update(update_rows, fields=update_fields, batch_size=batch_size)
        stats.skill_updates += len(update_rows)


def _upsert_occupations(
    occupation_payloads: list[dict[str, object]],
    stats: IngestionStats,
    batch_size: int,
) -> None:
    if not occupation_payloads:
        return

    uri_list = [payload["uri"] for payload in occupation_payloads]
    existing_map = {
        occupation.uri: occupation
        for occupation in ESCOOccupationCatalog.objects.filter(uri__in=uri_list)
    }
    create_rows = []
    update_rows = []
    update_fields = [
        "preferred_label_en",
        "preferred_label_fr",
        "alt_labels_en",
        "alt_labels_fr",
        "hidden_labels_en",
        "hidden_labels_fr",
        "search_text_multilingual",
        "isco_group",
        "code",
        "nace_code",
    ]

    for payload in occupation_payloads:
        current = existing_map.get(payload["uri"])
        if current is None:
            create_rows.append(ESCOOccupationCatalog(**payload))
            continue
        changed_fields = _update_changed_fields(current, payload, update_fields)
        if changed_fields:
            update_rows.append(current)

    if create_rows:
        ESCOOccupationCatalog.objects.bulk_create(create_rows, batch_size=batch_size)
        stats.occupation_creates += len(create_rows)
    if update_rows:
        ESCOOccupationCatalog.objects.bulk_update(update_rows, fields=update_fields, batch_size=batch_size)
        stats.occupation_updates += len(update_rows)


def _upsert_relations(
    relation_keys: set[tuple[str, str, str]],
    stats: IngestionStats,
    batch_size: int,
) -> None:
    if not relation_keys:
        return

    occupation_uris = sorted({item[0] for item in relation_keys})
    skill_uris = sorted({item[1] for item in relation_keys})
    occupation_map = dict(
        ESCOOccupationCatalog.objects.filter(uri__in=occupation_uris).values_list("uri", "id")
    )
    skill_map = dict(
        ESCOSkill.objects.filter(uri__in=skill_uris).values_list("uri", "id")
    )

    desired_relations = []
    for occupation_uri, skill_uri, relation_type in relation_keys:
        occupation_id = occupation_map.get(occupation_uri)
        skill_id = skill_map.get(skill_uri)
        if occupation_id is None or skill_id is None:
            stats.missing_relation_targets += 1
            continue
        desired_relations.append((occupation_id, skill_id, relation_type))

    existing_relation_keys = set(
        ESCOOccupationSkillRelation.objects.filter(
            occupation_id__in=[item[0] for item in desired_relations],
            skill_id__in=[item[1] for item in desired_relations],
        ).values_list("occupation_id", "skill_id", "relation_type")
    )

    create_rows = []
    for relation_key in desired_relations:
        if relation_key in existing_relation_keys:
            stats.relation_existing += 1
            continue
        create_rows.append(
            ESCOOccupationSkillRelation(
                occupation_id=relation_key[0],
                skill_id=relation_key[1],
                relation_type=relation_key[2],
            )
        )

    if create_rows:
        ESCOOccupationSkillRelation.objects.bulk_create(create_rows, batch_size=batch_size)
        stats.relation_creates += len(create_rows)


def import_esco_catalog(base_dir: Path, *, batch_size: int = 1000) -> IngestionStats:
    stats = IngestionStats()
    base_path = Path(base_dir)

    skill_rows_by_uri: dict[str, dict[str, object]] = {}
    occupation_rows_by_uri: dict[str, dict[str, object]] = {}
    relation_keys: set[tuple[str, str, str]] = set()

    _, skill_rows_en = _read_csv_rows(base_path / "skills_en.csv", stats)
    _, skill_rows_fr = _read_csv_rows(base_path / "skills_fr.csv", stats)
    _merge_skill_language_rows(skill_rows_en, "en", skill_rows_by_uri, stats)
    _merge_skill_language_rows(skill_rows_fr, "fr", skill_rows_by_uri, stats)

    _, occupation_rows_en = _read_csv_rows(base_path / "occupations_en.csv", stats)
    _, occupation_rows_fr = _read_csv_rows(base_path / "occupations_fr.csv", stats)
    _merge_occupation_language_rows(occupation_rows_en, "en", occupation_rows_by_uri, stats)
    _merge_occupation_language_rows(occupation_rows_fr, "fr", occupation_rows_by_uri, stats)

    _, relation_rows_en = _read_csv_rows(base_path / "occupationSkillRelations_en.csv", stats)
    _, relation_rows_fr = _read_csv_rows(base_path / "occupationSkillRelations_fr.csv", stats)
    relation_keys.update(_collect_relation_keys(relation_rows_en, stats))
    relation_keys.update(_collect_relation_keys(relation_rows_fr, stats))

    skill_payloads = [_normalize_skill_payload(payload) for payload in skill_rows_by_uri.values()]
    occupation_payloads = [
        _normalize_occupation_payload(payload) for payload in occupation_rows_by_uri.values()
    ]

    with transaction.atomic():
        _upsert_skills(skill_payloads, stats, batch_size)
        _upsert_occupations(occupation_payloads, stats, batch_size)
        _upsert_relations(relation_keys, stats, batch_size)

    return stats
