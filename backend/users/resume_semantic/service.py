from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from django.db import transaction
from django.utils import timezone

from .esco_mapping import map_to_esco
from .extraction import extract_skill_candidates
from .models import (
    SEMANTIC_RESUME_VERSION,
    SEMANTIC_STATUS_EMPTY,
    SEMANTIC_STATUS_FAILED,
    SEMANTIC_STATUS_SKIPPED,
    SEMANTIC_STATUS_SUCCEEDED,
    ResumeSemanticSignals,
)
from .normalization import clean_resume_semantic_text, detect_languages
from .scoring import semantic_confidence


logger = logging.getLogger(__name__)

MAX_SEMANTIC_TEXT_CHARS = 12000
MAX_SEMANTIC_ERROR_CHARS = 500


def _content_hash(text: str) -> str:
    payload = f"{SEMANTIC_RESUME_VERSION}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_error(exc: Exception) -> str:
    return (str(exc).strip() or exc.__class__.__name__)[:MAX_SEMANTIC_ERROR_CHARS]


def enrich_resume_text(
    text: str,
    *,
    use_model: bool = True,
    allow_semantic_mapping: bool = True,
) -> ResumeSemanticSignals:
    started = time.monotonic()
    cleaned = clean_resume_semantic_text(text, max_chars=MAX_SEMANTIC_TEXT_CHARS)
    if not cleaned:
        return ResumeSemanticSignals(warnings=["empty_resume_text"])

    languages = detect_languages(cleaned)
    candidates = extract_skill_candidates(cleaned, use_model=use_model, max_chars=MAX_SEMANTIC_TEXT_CHARS)
    mapped = map_to_esco(
        [candidate.text for candidate in candidates],
        allow_semantic=allow_semantic_mapping,
    )
    skills = []
    domains = []
    tools = []
    for item in mapped:
        kind = item["kind"]
        canonical = str(item["canonical"])
        if kind == "domain":
            domains.append(canonical)
        elif kind == "tool":
            tools.append(canonical)
        else:
            skills.append(canonical)

    confidence = semantic_confidence(
        candidates=candidates,
        mapped_count=len(mapped),
        text_length=len(cleaned),
        language_count=len(languages),
    )
    warnings = []
    if time.monotonic() - started > 20.0:
        warnings.append("semantic_processing_exceeded_target_runtime")

    return ResumeSemanticSignals(
        skills=skills,
        domains=domains,
        tools=tools,
        languages_detected=languages,
        semantic_confidence=confidence,
        raw_candidates=candidates,
        mapped_candidates=mapped,
        warnings=warnings,
    )


def clear_resume_semantics(resume: Any, *, status: str, error: str = "") -> None:
    resume.extracted_skills = []
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
    use_model: bool = True,
    allow_semantic_mapping: bool = True,
) -> dict[str, Any]:
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

    try:
        signals = enrich_resume_text(
            text,
            use_model=use_model,
            allow_semantic_mapping=allow_semantic_mapping,
        )
    except Exception as exc:
        logger.exception(
            "resume semantic enrichment failed resume_id=%s",
            getattr(resume, "pk", None),
        )
        clear_resume_semantics(resume, status=SEMANTIC_STATUS_FAILED, error=_safe_error(exc))
        return {
            "status": SEMANTIC_STATUS_FAILED,
            "resume_id": getattr(resume, "pk", None),
            "error": _safe_error(exc),
        }

    with transaction.atomic():
        resume.extracted_skills = signals.skills
        resume.extracted_domains = signals.domains
        resume.extracted_tools = signals.tools
        resume.extracted_languages = signals.languages_detected
        resume.semantic_resume_version = SEMANTIC_RESUME_VERSION
        resume.semantic_resume_content_hash = content_hash
        resume.semantic_resume_updated_at = timezone.now()
        resume.semantic_resume_confidence = signals.semantic_confidence
        resume.semantic_resume_status = SEMANTIC_STATUS_SUCCEEDED if signals.has_structured_signal() else SEMANTIC_STATUS_EMPTY
        resume.semantic_resume_error = ""
        resume.semantic_resume_metadata = {
            "raw_candidates": [candidate.as_dict() for candidate in signals.raw_candidates[:40]],
            "mapped_candidates": signals.mapped_candidates[:40],
            "warnings": signals.warnings,
        }
        resume.save(
            update_fields=[
                "extracted_skills",
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
        "languages_detected": signals.languages_detected,
        "semantic_confidence": signals.semantic_confidence,
    }

