from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import (
    SEMANTIC_RESUME_VERSION,
    SEMANTIC_STATUS_EMPTY,
    SEMANTIC_STATUS_FAILED,
    SEMANTIC_STATUS_SKIPPED,
    SEMANTIC_STATUS_SUCCEEDED,
    ResumeSemanticSignals,
)
from .normalization import clean_resume_semantic_text
from .structured_llm import (
    StructuredResumeExtractionError,
    extract_structured_resume_signals,
)


logger = logging.getLogger(__name__)

MAX_SEMANTIC_TEXT_CHARS = 12000
MAX_SEMANTIC_ERROR_CHARS = 500
NORMALIZATION_SKIPPED_MESSAGE = "Skipped: Qwen structured resume extraction is the official CV pipeline."


def _content_hash(text: str) -> str:
    payload = f"{SEMANTIC_RESUME_VERSION}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_error(exc: Exception) -> str:
    return (str(exc).strip() or exc.__class__.__name__)[:MAX_SEMANTIC_ERROR_CHARS]


def _raw_skill_candidates(signals: ResumeSemanticSignals) -> list[str]:
    output: list[str] = []
    seen = set()
    for candidate in signals.raw_candidates or []:
        text = str(getattr(candidate, "text", "") or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _raw_skill_hash(values: list[str]) -> str:
    payload = json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resume_metadata(signals: ResumeSemanticSignals) -> dict[str, Any]:
    return {
        "raw_candidates": [candidate.as_dict() for candidate in signals.raw_candidates[:40]],
        "business_families": signals.business_families,
        "family_confidence": round(float(signals.family_confidence or 0.0), 4),
        "canonical_role": signals.canonical_role,
        "target_roles": signals.target_roles,
        "llm_enrichment": signals.llm_enrichment,
        "structured_extraction_enabled": True,
        "structured_extraction_error": "",
        "warnings": signals.warnings,
    }


def clear_resume_semantics(resume: Any, *, status: str, error: str = "") -> None:
    resume.extracted_skills = []
    resume.extracted_raw_skills = []
    resume.extracted_normalized_skills = []
    resume.extracted_skills_normalization_hash = ""
    resume.extracted_skills_normalization_updated_at = timezone.now()
    resume.extracted_skills_normalization_error = ""
    resume.extracted_domains = []
    resume.extracted_tools = []
    resume.extracted_languages = []
    resume.semantic_resume_version = SEMANTIC_RESUME_VERSION
    resume.semantic_resume_content_hash = ""
    resume.semantic_resume_updated_at = timezone.now()
    resume.semantic_resume_confidence = 0.0
    resume.semantic_resume_status = status
    resume.semantic_resume_error = error[:MAX_SEMANTIC_ERROR_CHARS]
    resume.semantic_resume_metadata = {}
    resume.save(
        update_fields=[
            "extracted_skills",
            "extracted_raw_skills",
            "extracted_normalized_skills",
            "extracted_skills_normalization_hash",
            "extracted_skills_normalization_updated_at",
            "extracted_skills_normalization_error",
            "extracted_domains",
            "extracted_tools",
            "extracted_languages",
            "semantic_resume_version",
            "semantic_resume_content_hash",
            "semantic_resume_updated_at",
            "semantic_resume_confidence",
            "semantic_resume_status",
            "semantic_resume_error",
            "semantic_resume_metadata",
        ]
    )


def process_profile_resume_semantics(
    resume: Any,
    *,
    force: bool = False,
    use_model: bool = False,
    allow_semantic_mapping: bool = False,
    use_llm: bool = False,
    normalize_skills: bool = False,
    structured_llm_enabled: bool = True,
    structured_llm_fallback_enabled: bool = False,
) -> dict[str, Any]:
    """Run the official CV semantic pipeline.

    The previous lexical/fallback pipeline was intentionally removed from
    this path. Deprecated keyword arguments remain accepted so callers in
    Celery tasks, management commands and tests do not need a risky synchronized
    rewrite before delivery.
    """
    del use_model, allow_semantic_mapping, use_llm, normalize_skills, structured_llm_fallback_enabled

    text = clean_resume_semantic_text(
        getattr(resume, "parsed_text", "") or getattr(resume, "resume_text_embedding_source", ""),
        max_chars=MAX_SEMANTIC_TEXT_CHARS,
    )
    if not text:
        clear_resume_semantics(resume, status=SEMANTIC_STATUS_EMPTY)
        return {"status": SEMANTIC_STATUS_EMPTY, "resume_id": getattr(resume, "pk", None)}

    content_hash = _content_hash(text)
    if (
        not force
        and getattr(resume, "semantic_resume_content_hash", "") == content_hash
        and getattr(resume, "semantic_resume_version", "") == SEMANTIC_RESUME_VERSION
        and getattr(resume, "semantic_resume_updated_at", None)
    ):
        return {
            "status": SEMANTIC_STATUS_SKIPPED,
            "reason": "fresh",
            "resume_id": getattr(resume, "pk", None),
        }

    if not structured_llm_enabled:
        error = "Qwen structured resume extraction is disabled."
        clear_resume_semantics(resume, status=SEMANTIC_STATUS_FAILED, error=error)
        return {
            "status": SEMANTIC_STATUS_FAILED,
            "resume_id": getattr(resume, "pk", None),
            "error": error,
        }

    try:
        signals = extract_structured_resume_signals(text)
    except StructuredResumeExtractionError as exc:
        logger.warning(
            "structured resume extraction failed resume_id=%s error=%s",
            getattr(resume, "pk", None),
            _safe_error(exc),
        )
        clear_resume_semantics(resume, status=SEMANTIC_STATUS_FAILED, error=_safe_error(exc))
        return {
            "status": SEMANTIC_STATUS_FAILED,
            "resume_id": getattr(resume, "pk", None),
            "error": _safe_error(exc),
        }
    except Exception as exc:  # noqa: BLE001 - persist failure instead of leaving PENDING
        logger.exception("resume semantic extraction crashed resume_id=%s", getattr(resume, "pk", None))
        clear_resume_semantics(resume, status=SEMANTIC_STATUS_FAILED, error=_safe_error(exc))
        return {
            "status": SEMANTIC_STATUS_FAILED,
            "resume_id": getattr(resume, "pk", None),
            "error": _safe_error(exc),
        }

    extracted_raw_skills = _raw_skill_candidates(signals)
    with transaction.atomic():
        resume.extracted_skills = signals.skills
        resume.extracted_raw_skills = extracted_raw_skills
        resume.extracted_normalized_skills = []
        resume.extracted_skills_normalization_hash = _raw_skill_hash(extracted_raw_skills)
        resume.extracted_skills_normalization_updated_at = timezone.now()
        resume.extracted_skills_normalization_error = NORMALIZATION_SKIPPED_MESSAGE
        resume.extracted_domains = signals.domains
        resume.extracted_tools = signals.tools
        resume.extracted_languages = signals.languages_detected
        resume.semantic_resume_version = SEMANTIC_RESUME_VERSION
        resume.semantic_resume_content_hash = content_hash
        resume.semantic_resume_updated_at = timezone.now()
        resume.semantic_resume_confidence = signals.semantic_confidence
        resume.semantic_resume_status = SEMANTIC_STATUS_SUCCEEDED if signals.has_structured_signal() else SEMANTIC_STATUS_EMPTY
        resume.semantic_resume_error = ""
        resume.semantic_resume_metadata = _resume_metadata(signals)
        resume.save(
            update_fields=[
                "extracted_skills",
                "extracted_raw_skills",
                "extracted_normalized_skills",
                "extracted_skills_normalization_hash",
                "extracted_skills_normalization_updated_at",
                "extracted_skills_normalization_error",
                "extracted_domains",
                "extracted_tools",
                "extracted_languages",
                "semantic_resume_version",
                "semantic_resume_content_hash",
                "semantic_resume_updated_at",
                "semantic_resume_confidence",
                "semantic_resume_status",
                "semantic_resume_error",
                "semantic_resume_metadata",
            ]
        )

    return {
        "status": resume.semantic_resume_status,
        "resume_id": getattr(resume, "pk", None),
        "skills": signals.skills,
        "domains": signals.domains,
        "tools": signals.tools,
        "business_families": signals.business_families,
        "family_confidence": signals.family_confidence,
        "canonical_role": signals.canonical_role,
        "target_roles": signals.target_roles,
        "languages_detected": signals.languages_detected,
        "semantic_confidence": signals.semantic_confidence,
        "normalized_skills_count": 0,
        "matched_count": 0,
        "unmatched_count": 0,
        "official_matches": 0,
    }


def refresh_resume_skill_normalization_from_existing_candidates(
    resume: Any,
    *,
    force: bool = False,
) -> dict[str, Any]:
    del force
    return {
        "status": SEMANTIC_STATUS_SKIPPED,
        "reason": "resume_skill_normalization_removed_from_official_cv_pipeline",
        "resume_id": getattr(resume, "pk", None),
        "normalized_skills_count": 0,
        "matched_count": 0,
        "unmatched_count": 0,
        "official_matches": 0,
    }
