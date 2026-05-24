from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from ai.esco_mapper import normalize_text
from ai.esco_skill_normalization import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_SIMILARITY_THRESHOLD,
    ESCOSkillNormalizationResult,
    normalize_skills_to_esco,
)


logger = logging.getLogger(__name__)

MAX_SKILL_ITEMS = 100
MAX_SKILL_LENGTH = 160
MAX_NORMALIZATION_ERROR_CHARS = 500
OFFICIAL_ESCO_SKILL_URI_PREFIX = "http://data.europa.eu/esco/skill/"


@dataclass(frozen=True)
class SkillNormalizationStoragePayload:
    raw_skills: list[str]
    normalized_skills: list[dict[str, object]]
    content_hash: str


@dataclass(frozen=True)
class SkillNormalizationEntrySummary:
    total_entries: int
    matched_entries: int
    official_matches: int
    legacy_matches: int
    unmatched_entries: int
    matched_canonical_skills: tuple[str, ...]
    unmatched_raw_skills: tuple[str, ...]
    unmatched_reasons: tuple[str, ...]


def is_official_esco_skill_uri(uri: str | None) -> bool:
    value = str(uri or "").strip()
    return value.startswith(OFFICIAL_ESCO_SKILL_URI_PREFIX)


def clean_skill_storage_list(values) -> list[str]:
    if values is None:
        return []

    if isinstance(values, str):
        raw_values = [values]
    elif isinstance(values, (list, tuple, set)):
        raw_values = list(values)
    else:
        raw_values = [values]

    cleaned = []
    seen = set()
    for item in raw_values:
        text = str(item or "").replace("\x00", " ").replace("\ufeff", " ").strip()
        if not text:
            continue
        text = " ".join(text.split())
        if len(text) > MAX_SKILL_LENGTH:
            text = text[:MAX_SKILL_LENGTH].rstrip()

        lookup_key = normalize_text(text) or text.casefold()
        if lookup_key in seen:
            continue
        seen.add(lookup_key)
        cleaned.append(text)
        if len(cleaned) >= MAX_SKILL_ITEMS:
            break

    return cleaned


def build_skill_storage_hash(raw_skills) -> str:
    cleaned = clean_skill_storage_list(raw_skills)
    stable_keys = [
        normalize_text(value) or value.casefold()
        for value in cleaned
    ]
    payload = "\n".join(stable_keys).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def safe_normalization_error(exc: Exception) -> str:
    return (str(exc).strip() or exc.__class__.__name__)[:MAX_NORMALIZATION_ERROR_CHARS]


def summarize_normalized_skill_entries(entries) -> SkillNormalizationEntrySummary:
    total_entries = 0
    matched_entries = 0
    official_matches = 0
    legacy_matches = 0
    unmatched_entries = 0
    matched_canonical_skills: list[str] = []
    unmatched_raw_skills: list[str] = []
    unmatched_reasons: list[str] = []

    if not isinstance(entries, (list, tuple)):
        entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        total_entries += 1

        esco_uri = str(entry.get("esco_uri") or "").strip()
        canonical_skill = str(entry.get("canonical_skill") or "").strip()
        raw_skill = str(entry.get("raw_skill") or "").strip()

        if esco_uri:
            matched_entries += 1
            if is_official_esco_skill_uri(esco_uri):
                official_matches += 1
            else:
                legacy_matches += 1
            if canonical_skill:
                matched_canonical_skills.append(canonical_skill)
            continue

        unmatched_entries += 1
        if raw_skill:
            unmatched_raw_skills.append(raw_skill)
        reason = str(entry.get("unmatched_reason") or "").strip()
        if reason:
            unmatched_reasons.append(reason)

    return SkillNormalizationEntrySummary(
        total_entries=total_entries,
        matched_entries=matched_entries,
        official_matches=official_matches,
        legacy_matches=legacy_matches,
        unmatched_entries=unmatched_entries,
        matched_canonical_skills=tuple(matched_canonical_skills),
        unmatched_raw_skills=tuple(unmatched_raw_skills),
        unmatched_reasons=tuple(unmatched_reasons),
    )


def _result_to_storage_dict(
    result: ESCOSkillNormalizationResult,
    *,
    official_only: bool,
) -> dict[str, object]:
    if official_only and result.esco_uri and not is_official_esco_skill_uri(result.esco_uri):
        return ESCOSkillNormalizationResult(
            raw_skill=result.raw_skill,
            canonical_skill=None,
            esco_uri=None,
            match_type="unmatched",
            canonical_skill_en=None,
            canonical_skill_fr=None,
            unmatched_reason="legacy_uri_filtered",
        ).as_dict()
    return result.as_dict()


def build_skill_normalization_payload(
    raw_skills,
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    official_only: bool = True,
) -> SkillNormalizationStoragePayload:
    cleaned_raw_skills = clean_skill_storage_list(raw_skills)
    content_hash = build_skill_storage_hash(cleaned_raw_skills)
    if not cleaned_raw_skills:
        return SkillNormalizationStoragePayload(
            raw_skills=[],
            normalized_skills=[],
            content_hash=content_hash,
        )

    results = normalize_skills_to_esco(
        cleaned_raw_skills,
        similarity_threshold=similarity_threshold,
        max_candidates=max_candidates,
    )
    return SkillNormalizationStoragePayload(
        raw_skills=cleaned_raw_skills,
        normalized_skills=[
            _result_to_storage_dict(result, official_only=official_only)
            for result in results
        ],
        content_hash=content_hash,
    )
