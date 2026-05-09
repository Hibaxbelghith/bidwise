"""
Shared employment normalization helpers.

This module is intentionally standalone for now: it defines canonical
vocabularies and deterministic normalization functions without changing
database persistence, recommendation scoring, embeddings, or API serializers.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


CONTRACT_TYPE_CDI = "CDI"
CONTRACT_TYPE_CDD = "CDD"
CONTRACT_TYPE_INTERNSHIP = "INTERNSHIP"
CONTRACT_TYPE_SIVP = "SIVP"
CONTRACT_TYPE_FREELANCE = "FREELANCE"
CONTRACT_TYPE_ALTERNANCE = "ALTERNANCE"
CONTRACT_TYPE_TEMPORARY_INTERIM = "TEMPORARY_INTERIM"
CONTRACT_TYPE_SEASONAL = "SEASONAL"
CONTRACT_TYPE_PUBLIC_SECTOR = "PUBLIC_SECTOR"

CANONICAL_CONTRACT_TYPES = (
    CONTRACT_TYPE_CDI,
    CONTRACT_TYPE_CDD,
    CONTRACT_TYPE_INTERNSHIP,
    CONTRACT_TYPE_SIVP,
    CONTRACT_TYPE_FREELANCE,
    CONTRACT_TYPE_ALTERNANCE,
    CONTRACT_TYPE_TEMPORARY_INTERIM,
    CONTRACT_TYPE_SEASONAL,
    CONTRACT_TYPE_PUBLIC_SECTOR,
)

WORK_MODE_REMOTE = "REMOTE"
WORK_MODE_HYBRID = "HYBRID"
WORK_MODE_ON_SITE = "ON_SITE"
WORK_MODE_UNSPECIFIED = "UNSPECIFIED"

CANONICAL_WORK_MODES = (
    WORK_MODE_REMOTE,
    WORK_MODE_HYBRID,
    WORK_MODE_ON_SITE,
    WORK_MODE_UNSPECIFIED,
)

SCHEDULE_FULL_TIME = "FULL_TIME"
SCHEDULE_PART_TIME = "PART_TIME"
SCHEDULE_UNSPECIFIED = "UNSPECIFIED"

CANONICAL_SCHEDULES = (
    SCHEDULE_FULL_TIME,
    SCHEDULE_PART_TIME,
    SCHEDULE_UNSPECIFIED,
)


@dataclass(frozen=True)
class NormalizedContractValues:
    canonical: list[str]
    unknown: list[str]


CONTRACT_TYPE_ALIASES = {
    # Stable Tunisian/French employment contracts.
    "cdi": CONTRACT_TYPE_CDI,
    "contrat a duree indeterminee": CONTRACT_TYPE_CDI,
    "contrat duree indeterminee": CONTRACT_TYPE_CDI,
    "permanent": CONTRACT_TYPE_CDI,
    "permanent contract": CONTRACT_TYPE_CDI,
    "عقد غير محدد المدة": CONTRACT_TYPE_CDI,
    "cdd": CONTRACT_TYPE_CDD,
    "contrat a duree determinee": CONTRACT_TYPE_CDD,
    "contrat duree determinee": CONTRACT_TYPE_CDD,
    "fixed term": CONTRACT_TYPE_CDD,
    "fixed term contract": CONTRACT_TYPE_CDD,
    "contract": CONTRACT_TYPE_CDD,
    "contractuel": CONTRACT_TYPE_CDD,
    "عقد محدد المدة": CONTRACT_TYPE_CDD,
    # Internships and early-career programs.
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
    # Flexible work contracts.
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
    "intérim": CONTRACT_TYPE_TEMPORARY_INTERIM,
    "interim": CONTRACT_TYPE_TEMPORARY_INTERIM,
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
    "plein temps": SCHEDULE_FULL_TIME,
    "temps plein": SCHEDULE_FULL_TIME,
    "full time": SCHEDULE_FULL_TIME,
    "fulltime": SCHEDULE_FULL_TIME,
    "full": SCHEDULE_FULL_TIME,
    "دوام كامل": SCHEDULE_FULL_TIME,
    "mi temps": SCHEDULE_PART_TIME,
    "temps partiel": SCHEDULE_PART_TIME,
    "part time": SCHEDULE_PART_TIME,
    "parttime": SCHEDULE_PART_TIME,
    "partiel": SCHEDULE_PART_TIME,
    "دوام جزئي": SCHEDULE_PART_TIME,
}

_SPLIT_RE = re.compile(r"\s*(?:[-–—/,;|+&]|\bet\b|\bou\b|\bor\b)\s*", re.IGNORECASE)


def normalize_key(value: Any) -> str:
    """Return an accent-insensitive, case-insensitive lookup key."""
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


def clean_display_value(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip(" \t\r\n,;|/-")


def _coerce_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items: list[Any] = []
        for item in value:
            items.extend(_coerce_items(item))
        return items
    return [value]


def split_contract_values(value: Any) -> list[str]:
    """Split noisy single or multi-value contract strings into display tokens."""
    tokens: list[str] = []
    for item in _coerce_items(value):
        text = clean_display_value(item)
        if not text:
            continue
        for part in _SPLIT_RE.split(text):
            cleaned = clean_display_value(part)
            if cleaned:
                tokens.append(cleaned)
    return tokens


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def normalize_contract_values(value: Any, *, preserve_unknown: bool = True) -> NormalizedContractValues:
    """
    Normalize one or many contract/employment values.

    Unknown tokens are returned separately so callers can log, audit, or store
    them without polluting canonical preference or recommendation values.
    """
    canonical: list[str] = []
    unknown: list[str] = []
    seen_unknown: set[str] = set()

    for token in split_contract_values(value):
        key = normalize_key(token)
        if not key:
            continue

        mapped = CONTRACT_TYPE_ALIASES.get(key)
        if mapped:
            _append_unique(canonical, mapped)
            continue

        if key in WORK_MODE_ALIASES or key in SCHEDULE_ALIASES:
            continue

        if preserve_unknown and key not in seen_unknown:
            seen_unknown.add(key)
            unknown.append(token)

    return NormalizedContractValues(canonical=canonical, unknown=unknown)


def normalize_contract_types(value: Any) -> list[str]:
    """Return deduplicated canonical contract/employment types only."""
    return normalize_contract_values(value, preserve_unknown=False).canonical


def normalize_contract_type(value: Any) -> str | None:
    """Return the first canonical contract/employment type, if any."""
    values = normalize_contract_types(value)
    return values[0] if values else None


def normalize_work_mode(value: Any) -> str:
    for item in _coerce_items(value):
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


def normalize_schedule(value: Any) -> str:
    for item in _coerce_items(value):
        key = normalize_key(item)
        if not key:
            continue
        mapped = SCHEDULE_ALIASES.get(key)
        if mapped:
            return mapped
        for alias in ("temps partiel", "mi temps", "part time", "parttime", "partiel"):
            if alias in key:
                return SCHEDULE_PART_TIME
        for alias in ("plein temps", "temps plein", "full time", "fulltime"):
            if alias in key:
                return SCHEDULE_FULL_TIME
    return SCHEDULE_UNSPECIFIED


__all__ = [
    "CANONICAL_CONTRACT_TYPES",
    "CANONICAL_SCHEDULES",
    "CANONICAL_WORK_MODES",
    "CONTRACT_TYPE_ALIASES",
    "CONTRACT_TYPE_ALTERNANCE",
    "CONTRACT_TYPE_CDD",
    "CONTRACT_TYPE_CDI",
    "CONTRACT_TYPE_FREELANCE",
    "CONTRACT_TYPE_INTERNSHIP",
    "CONTRACT_TYPE_PUBLIC_SECTOR",
    "CONTRACT_TYPE_SEASONAL",
    "CONTRACT_TYPE_SIVP",
    "CONTRACT_TYPE_TEMPORARY_INTERIM",
    "NormalizedContractValues",
    "SCHEDULE_ALIASES",
    "SCHEDULE_FULL_TIME",
    "SCHEDULE_PART_TIME",
    "SCHEDULE_UNSPECIFIED",
    "WORK_MODE_ALIASES",
    "WORK_MODE_HYBRID",
    "WORK_MODE_ON_SITE",
    "WORK_MODE_REMOTE",
    "WORK_MODE_UNSPECIFIED",
    "clean_display_value",
    "normalize_contract_type",
    "normalize_contract_types",
    "normalize_contract_values",
    "normalize_key",
    "normalize_schedule",
    "normalize_work_mode",
    "split_contract_values",
]
