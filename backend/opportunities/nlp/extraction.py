"""
NLP extraction helpers for opportunity enrichment.

These functions keep the extraction regexes and keyword lookups outside the
enrichment orchestrator while preserving the existing behavior.
"""

import re
from typing import Any

from opportunities.nlp.skills import SKILLS
from opportunities.utils.text_parsing import (
    normalize_text as _normalize_text,
    normalize_token as _normalize_token,
)


_LANGUAGE_PATTERNS = {
    "français": re.compile(r"\bfran(?:c|ç)ais\b", flags=re.IGNORECASE),
    "anglais": re.compile(r"\banglais\b", flags=re.IGNORECASE),
    "arabe": re.compile(r"\barabe\b", flags=re.IGNORECASE),
}


_SOFT_SKILL_KEYWORDS = (
    "communication",
    "esprit d equipe",
    "teamwork",
    "autonomie",
    "autonome",
    "rigueur",
    "adaptabilite",
    "leadership",
    "organisation",
    "gestion du temps",
    "proactif",
    "proactive",
    "motivation",
    "analyse",
    "analytique",
    "problem solving",
    "resolution de problemes",
)


_SALARY_AMOUNT_TOKEN = r"(?:\d{1,3}(?:[\.\s]\d{3})+|\d{3,5})"
_RANGE_SALARY_RE = re.compile(
    rf"(?:entre\s+)?(?P<low>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)?\s*"
    rf"(?:a|à|-|et|au|to)\s*(?P<high>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)",
    flags=re.IGNORECASE,
)
_SINGLE_SALARY_RE = re.compile(
    rf"(?P<value>{_SALARY_AMOUNT_TOKEN})\s*(?:dt|tnd|dinars?)",
    flags=re.IGNORECASE,
)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ")


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


def _extract_amount_int(value: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except (TypeError, ValueError):
        return None


def _format_salary_single(amount: int) -> str:
    return f"{amount} TND"


def _format_salary_range(low: int, high: int) -> str:
    normalized_low = min(low, high)
    normalized_high = max(low, high)
    return f"{normalized_low} - {normalized_high} TND"


def find_salary(text: str) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    match = _RANGE_SALARY_RE.search(normalized)
    if match:
        low = _extract_amount_int(match.group("low"))
        high = _extract_amount_int(match.group("high"))
        if low is not None and high is not None:
            return _format_salary_range(low, high)

    match = _SINGLE_SALARY_RE.search(normalized)
    if match:
        amount = _extract_amount_int(match.group("value"))
        if amount is not None:
            return _format_salary_single(amount)

    return None


def find_skills(text: str) -> list[str]:
    normalized_text = _normalize_token(text)
    if not normalized_text:
        return []

    found: list[str] = []
    for skill in SKILLS:
        normalized_skill = _normalize_token(skill)
        if not normalized_skill:
            continue
        pattern = r"\b" + re.escape(normalized_skill).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, normalized_text):
            found.append(skill)
    return found


def find_soft_skills(text: str) -> list[str]:
    raw = _as_text(text)
    if not raw:
        return []

    candidates: list[str] = []
    bullet_pattern = re.compile(r"^\s*(?:[-*â€¢Â·â–ªâ€£â€“]+|\d+[\.)])\s*")

    for line in re.split(r"[\r\n]+", raw):
        if not line.strip():
            continue

        is_bullet = bullet_pattern.match(line) is not None
        cleaned_line = bullet_pattern.sub("", line, count=1)
        for chunk in re.split(r"\s*[;|]\s*", cleaned_line):
            candidate = _normalize_text(chunk)
            if not candidate:
                continue
            if not (10 <= len(candidate) <= 80):
                continue
            if len(candidate.split()) > 12:
                continue
            if not is_bullet and len(candidate) > 70:
                continue
            candidates.append(candidate)

    soft_skills: list[str] = []
    for candidate in candidates:
        token = _normalize_token(candidate)
        if any(keyword in token for keyword in _SOFT_SKILL_KEYWORDS):
            soft_skills.append(candidate)

    return _merge_unique(soft_skills)


def find_languages(text: str) -> list[str] | None:
    found: list[str] = []
    for language, pattern in _LANGUAGE_PATTERNS.items():
        if pattern.search(text):
            found.append(language)
    return found or None


_find_skills = find_skills
_find_soft_skills = find_soft_skills
_find_languages_fallback = find_languages
_find_salary = find_salary


__all__ = [
    "find_skills",
    "find_soft_skills",
    "find_languages",
    "find_salary",
]

