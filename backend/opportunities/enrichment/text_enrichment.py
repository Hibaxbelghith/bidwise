"""
Free-text enrichment orchestration for opportunities.

This module merges structured source data with NLP-derived fields and keeps the
overall enrichment contract stable. NLP extraction itself lives in
``opportunities.nlp.extraction`` so this layer can focus on orchestration.
"""

import logging
import re
from typing import Any

from opportunities.nlp.extraction import (
    find_languages,
    find_salary,
    find_skills,
    find_soft_skills,
)
from opportunities.nlp.skills import SKILLS  # noqa: F401 - legacy import surface
from opportunities.utils.text_parsing import (
    normalize_text as _normalize_text,
    normalize_token as _normalize_token,
    parse_experience_bounds,
)


logger = logging.getLogger(__name__)


_find_skills = find_skills
_find_soft_skills = find_soft_skills
_find_languages_fallback = find_languages
_find_salary = find_salary


_EXPERIENCE_RANGE_RE = re.compile(
    r"(?:entre\s*)?(\d+)\s*(?:ans|years)?\s*(?:à|a|-|et)\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_SINGLE_RE = re.compile(r"(\d+)\s*(?:ans|years)\b", flags=re.IGNORECASE)
_EXPERIENCE_LESS_THAN_RE = re.compile(
    r"<\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_BEGINNER_RE = re.compile(
    r"debutant\s*(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_MORE_THAN_RE = re.compile(
    r"(?:plus(?:\s+que)?\s*|>\s*)(\d+)\s*(?:ans|years)\b",
    flags=re.IGNORECASE,
)
_EXPERIENCE_LESS_THAN_ONE_YEAR_TOKEN = "moins d un an"


_EXPERIENCE_KEYWORD_TOKEN = "experience"
_EXPERIENCE_PHRASE_TOKEN = "ans d experience"
_EXPERIENCE_IGNORE_PATTERNS = (
    "depuis",
    "creation",
    "fondee",
    "notre entreprise",
    "notre client",
    "a propos de l opportunite",
    "entreprise specialisee",
    "forte de plus de",
)
_MAX_REASONABLE_EXPERIENCE_YEARS = 20


def _safe_defaults() -> dict[str, Any]:
    return {
        "salary": None,
        "experience_min": None,
        "experience_max": None,
        "experience_years": None,
        "skills": [],
        "languages_fallback": None,
    }


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ")


def _to_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _merge_unique(items: list[str]) -> list[str]:
    merged: list[str] = []
    seen_tokens: set[str] = set()
    for item in items:
        text = _normalize_text(item)
        if not text:
            continue
        token = _normalize_token(text)
        if token:
            if token in seen_tokens:
                continue
            seen_tokens.add(token)
        elif text in merged:
            continue

        merged.append(text)
    return merged


def _sanitize_experience_bounds(
    minimum: int | None,
    maximum: int | None,
) -> tuple[int | None, int | None]:
    minimum, maximum = _normalize_experience_bounds(minimum, maximum)

    if minimum is not None and minimum > _MAX_REASONABLE_EXPERIENCE_YEARS:
        return None, None

    if maximum is not None and maximum > _MAX_REASONABLE_EXPERIENCE_YEARS:
        maximum = None

    return minimum, maximum


def _normalize_structured_skills(value: Any) -> list[str]:
    if isinstance(value, list):
        return _merge_unique([_normalize_text(item) for item in value])

    text = _normalize_text(value)
    if not text:
        return []

    parts = re.split(r"\s*[-,;|/]\s*", text)
    return _merge_unique(parts)


def _normalize_experience_bounds(
    minimum: int | None,
    maximum: int | None,
) -> tuple[int | None, int | None]:
    if minimum is not None and maximum is not None:
        if minimum > maximum:
            return maximum, minimum
        return minimum, maximum

    if minimum is None and maximum is not None:
        return maximum, maximum

    return minimum, maximum


def _has_experience_context(text: str) -> bool:
    token = _normalize_token(text)
    if not token:
        return False
    if _EXPERIENCE_PHRASE_TOKEN in token:
        return True
    return _EXPERIENCE_KEYWORD_TOKEN in token


def _has_ignored_experience_context(text: str) -> bool:
    token = _normalize_token(text)
    if not token:
        return False
    return any(pattern in token for pattern in _EXPERIENCE_IGNORE_PATTERNS)


def _iter_experience_segments(text: str):
    raw = _as_text(text)
    for line in re.split(r"[\r\n]+", raw):
        if not line.strip():
            continue
        for segment in re.split(r"[.;]", line):
            candidate = _normalize_text(segment)
            if candidate:
                yield candidate


def _find_experience_from_description(text: str) -> tuple[int | None, int | None]:
    for segment in _iter_experience_segments(text):
        if not _has_experience_context(segment):
            continue
        if _has_ignored_experience_context(segment):
            continue

        minimum, maximum = parse_experience_bounds(segment)
        if minimum is None and maximum is None:
            continue

        # Guard against company-age style false positives (e.g. "plus de 24 ans d'expérience").
        if minimum is not None and minimum > _MAX_REASONABLE_EXPERIENCE_YEARS:
            continue

        return _normalize_experience_bounds(minimum, maximum)

    return None, None


def _resolve_experience(
    opportunity: Any,
    structured_experience: str,
    description: str,
) -> tuple[int | None, int | None]:
    existing_min = _to_optional_int(_get_value(opportunity, "experience_min"))
    existing_max = _to_optional_int(_get_value(opportunity, "experience_max"))
    if existing_min is not None or existing_max is not None:
        return _sanitize_experience_bounds(existing_min, existing_max)

    if structured_experience:
        return None, None

    minimum, maximum = _find_experience_from_description(description)
    return _sanitize_experience_bounds(minimum, maximum)


def enrich_opportunity_text(opportunity: Any) -> dict[str, Any]:
    """
    Deterministic free-text enrichment.

    Safety guarantees:
    - no exception escapes
    - scalar fields return None when unavailable
    - skills always returns a list
    - structured languages are never overridden
    """

    defaults = _safe_defaults()
    try:
        raw_description = _as_text(_get_value(opportunity, "description"))
        raw_qualifications = _as_text(_get_value(opportunity, "job_qualifications"))
        raw_skill_context = "\n".join(part for part in [raw_description, raw_qualifications] if part)
        description = _normalize_text(raw_description)
        qualifications = _normalize_text(raw_qualifications)
        text_context = _normalize_text("\n".join(part for part in [description, qualifications] if part))
        structured_experience = _normalize_text(_get_value(opportunity, "experience"))
        structured_salary = _normalize_text(_get_value(opportunity, "salary"))
        structured_skills = _get_value(opportunity, "skills")

        if not text_context and not structured_experience and not structured_salary and not structured_skills:
            return defaults

        structured_languages = _get_value(opportunity, "languages")
        has_structured_languages = isinstance(structured_languages, list) and len(structured_languages) > 0

        salary = None
        if structured_salary:
            salary = find_salary(structured_salary) or structured_salary
        elif text_context:
            salary = find_salary(text_context)

        experience_min, experience_max = _resolve_experience(
            opportunity=opportunity,
            structured_experience=structured_experience,
            description=raw_description,
        )
        experience_years = experience_min

        normalized_structured_skills = _normalize_structured_skills(structured_skills)
        hard_skills = find_skills(text_context)
        soft_skills = find_soft_skills(raw_skill_context)
        skills = _merge_unique([*normalized_structured_skills, *hard_skills, *soft_skills])

        languages_fallback = None if has_structured_languages else find_languages(text_context)

        return {
            "salary": salary,
            "experience_min": experience_min,
            "experience_max": experience_max,
            "experience_years": experience_years,
            "skills": skills,
            "languages_fallback": languages_fallback,
        }
    except Exception as exc:
        logger.warning("Enrichment failed", exc_info=exc)
        return defaults
