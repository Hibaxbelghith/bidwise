from __future__ import annotations

import logging
import os
import re
from functools import lru_cache

from django.conf import settings

from .esco_mapping import ESCO_SKILLS
from .models import SkillCandidate
from .normalization import clean_resume_semantic_text, contains_phrase, normalize_lookup_key


logger = logging.getLogger(__name__)

SKILL_EXTRACTION_MODEL = getattr(
    settings,
    "RESUME_SKILL_EXTRACTION_MODEL",
    os.getenv("RESUME_SKILL_EXTRACTION_MODEL", "jjzha/escoxlmr_skill_extraction"),
)
MAX_CANDIDATES = int(getattr(settings, "RESUME_SEMANTIC_MAX_CANDIDATES", 80))
MODEL_MIN_CONFIDENCE = float(getattr(settings, "RESUME_SKILL_EXTRACTION_MIN_CONFIDENCE", 0.50))


TECH_PHRASES = tuple(
    sorted(
        {
            alias
            for skill in ESCO_SKILLS
            for alias in skill.aliases
        }
        | {
            "Django REST",
            "Django REST Framework",
            "CI/CD pipelines",
            "REST APIs",
            "PostgreSQL",
            "K8s",
            "PyTorch",
            "FastAPI",
            "GitHub Actions",
            "GitLab CI",
            "Incident Response",
            "Network Security",
            "Data pipelines",
            "ETL",
            "ELT",
        },
        key=lambda value: (-len(value), value.casefold()),
    )
)


@lru_cache(maxsize=1)
def _load_skill_pipeline():
    from transformers import pipeline

    logger.info("Loading resume skill extraction model '%s' on CPU", SKILL_EXTRACTION_MODEL)
    return pipeline(
        "token-classification",
        model=SKILL_EXTRACTION_MODEL,
        tokenizer=SKILL_EXTRACTION_MODEL,
        aggregation_strategy="simple",
        device=-1,
    )


def _model_candidates(text: str) -> list[SkillCandidate]:
    try:
        nlp = _load_skill_pipeline()
        rows = nlp(text)
    except Exception:
        logger.warning(
            "Resume skill extraction model unavailable; using deterministic phrase extraction.",
            exc_info=True,
        )
        return []

    candidates = []
    for row in rows:
        confidence = float(row.get("score") or 0.0)
        if confidence < MODEL_MIN_CONFIDENCE:
            continue
        label = str(row.get("word") or row.get("entity_group") or "").strip()
        if not label:
            continue
        candidates.append(
            SkillCandidate(
                text=label,
                source="escoxlmr",
                confidence=confidence,
                start=row.get("start"),
                end=row.get("end"),
            )
        )
        if len(candidates) >= MAX_CANDIDATES:
            break
    return candidates


def _phrase_candidates(text: str) -> list[SkillCandidate]:
    candidates = []
    seen = set()
    for phrase in TECH_PHRASES:
        if not contains_phrase(text, phrase):
            continue
        key = normalize_lookup_key(phrase)
        if key in seen:
            continue
        seen.add(key)
        match = re.search(re.escape(phrase), text, flags=re.IGNORECASE | re.UNICODE)
        candidates.append(
            SkillCandidate(
                text=phrase,
                source="lexical",
                confidence=0.90,
                start=match.start() if match else None,
                end=match.end() if match else None,
            )
        )
        if len(candidates) >= MAX_CANDIDATES:
            break
    return candidates


def extract_skill_candidates(
    text: str,
    *,
    use_model: bool = True,
    max_chars: int = 12000,
) -> list[SkillCandidate]:
    cleaned = clean_resume_semantic_text(text, max_chars=max_chars)
    if not cleaned:
        return []

    candidates = []
    if use_model:
        candidates.extend(_model_candidates(cleaned))
    candidates.extend(_phrase_candidates(cleaned))

    deduped = []
    seen = set()
    for candidate in sorted(candidates, key=lambda item: (-(item.confidence or 0.0), item.text.casefold())):
        key = normalize_lookup_key(candidate.text)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
        if len(deduped) >= MAX_CANDIDATES:
            break
    return deduped

