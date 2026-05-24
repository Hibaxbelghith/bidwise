import logging
import re
import unicodedata
from functools import lru_cache

from ai.models import ESCOOccupation


logger = logging.getLogger(__name__)


def normalize_text(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9\s+-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


@lru_cache(maxsize=1)
def _load_esco_indexes():
    role_map = {}
    skill_map = {}
    title_aliases = []

    try:
        occupations = list(
            ESCOOccupation.objects.only(
                "uri",
                "preferred_label",
                "family",
                "alternate_labels",
                "related_skills",
            )
        )
    except Exception as exc:
        logger.warning(
            "ESCO lookup cache unavailable; using empty in-memory indexes: %s",
            exc,
        )
        return role_map, skill_map, tuple(title_aliases)

    for occupation in occupations:
        labels = [occupation.preferred_label, *list(occupation.alternate_labels or [])]
        for label in labels:
            key = normalize_text(label)
            if not key:
                continue
            role_map.setdefault(key, occupation)
            title_aliases.append((key, str(occupation.family or "").strip()))

        for related_skill in list(occupation.related_skills or []):
            key = normalize_text(related_skill)
            if not key:
                continue
            skill_map.setdefault(
                key,
                {
                    "skill": related_skill,
                    "family": occupation.family,
                    "occupation": occupation.preferred_label,
                },
            )

    title_aliases.sort(key=lambda item: len(item[0]), reverse=True)
    return role_map, skill_map, tuple(title_aliases)


def clear_esco_mapper_cache():
    _load_esco_indexes.cache_clear()


def map_role_to_esco(role):
    key = normalize_text(role)
    if not key:
        return None

    role_map, _, _ = _load_esco_indexes()
    return role_map.get(key)


def map_skill_to_esco(skill):
    key = normalize_text(skill)
    if not key:
        return None

    _, skill_map, _ = _load_esco_indexes()
    payload = skill_map.get(key)
    return dict(payload) if payload else None


def role_families_for_values(values):
    families = set()
    items = values if isinstance(values, (list, tuple, set)) else [values]
    for value in items:
        occupation = map_role_to_esco(value)
        family = str(getattr(occupation, "family", "") or "").strip()
        if family:
            families.add(family)
    return families


def skill_families_for_values(values):
    families = set()
    items = values if isinstance(values, (list, tuple, set)) else [values]
    for value in items:
        payload = map_skill_to_esco(value)
        family = str((payload or {}).get("family") or "").strip()
        if family:
            families.add(family)
    return families


def role_families_for_text(text):
    normalized_text = normalize_text(text)
    if not normalized_text:
        return set()

    padded_text = f" {normalized_text} "
    _, _, title_aliases = _load_esco_indexes()
    families = set()
    for alias, family in title_aliases:
        if family and f" {alias} " in padded_text:
            families.add(family)
    return families
