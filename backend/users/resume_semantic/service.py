from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import Counter
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ai.business_families import normalize_family_set
from ai.esco_skill_storage import (
    SkillNormalizationStoragePayload,
    build_skill_normalization_payload,
    build_skill_storage_hash,
    clean_skill_storage_list,
    safe_normalization_error,
    summarize_normalized_skill_entries,
)

from .esco_mapping import map_to_esco
from .candidate_quality import filter_resume_skill_candidates
from .extraction import extract_skill_candidates
from .models import (
    SEMANTIC_RESUME_VERSION,
    SEMANTIC_STATUS_EMPTY,
    SEMANTIC_STATUS_FAILED,
    SEMANTIC_STATUS_SKIPPED,
    SEMANTIC_STATUS_SUCCEEDED,
    ResumeSemanticSignals,
    SkillCandidate,
)
from .normalization import clean_resume_semantic_text, detect_languages
from .scoring import semantic_confidence


logger = logging.getLogger(__name__)

MAX_SEMANTIC_TEXT_CHARS = 12000
MAX_SEMANTIC_ERROR_CHARS = 500
RESUME_CANDIDATE_QUALITY_VERSION = "resume-candidate-quality-v1"


def _content_hash(text: str) -> str:
    payload = f"{SEMANTIC_RESUME_VERSION}\n{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_error(exc: Exception) -> str:
    return (str(exc).strip() or exc.__class__.__name__)[:MAX_SEMANTIC_ERROR_CHARS]


def _raw_skill_candidates(signals: ResumeSemanticSignals) -> list[str]:
    seen = set()
    output = []
    for candidate in list(signals.raw_candidates or []):
        text = str(getattr(candidate, "text", "") or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
    return output


def _resume_candidate_quality_metadata(signals: ResumeSemanticSignals) -> dict[str, Any]:
    rejected_reason_counts = Counter(
        candidate.reason
        for candidate in signals.rejected_candidates
        if str(candidate.reason or "").strip()
    )
    return {
        "accepted_count": len(signals.raw_candidates),
        "rejected_count": len(signals.rejected_candidates),
        "rejected_reason_counts": dict(rejected_reason_counts),
        "candidate_quality_version": RESUME_CANDIDATE_QUALITY_VERSION,
    }


def _dedupe_strings(*values: Any) -> list[str]:
    output = []
    seen = set()
    for value in values:
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = value
        else:
            raw_items = []
        for item in raw_items:
            text = str(item or "").strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            output.append(text)
    return output


def _resume_llm_enabled() -> bool:
    return bool(getattr(settings, "LLM_ENRICHMENT_ENABLED", False))


def _safe_confidence(value: Any) -> float:
    try:
        confidence = float(value or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    return max(0.0, min(1.0, confidence))


def _normalized_search_text(value: Any) -> str:
    text = str(value or "").casefold()
    return re.sub(r"[^\w+#./-]+", " ", text, flags=re.UNICODE)


def _label_is_evidenced_in_text(label: str, cleaned_text: str) -> bool:
    label_text = _normalized_search_text(label).strip()
    if not label_text:
        return False
    haystack = _normalized_search_text(cleaned_text)
    compact_label = re.sub(r"[\s./-]+", "", label_text)
    compact_haystack = re.sub(r"[\s./-]+", "", haystack)
    return label_text in haystack or bool(compact_label and compact_label in compact_haystack)


def _filter_evidenced_llm_labels(values: Any, cleaned_text: str) -> list[str]:
    return [
        value
        for value in _dedupe_strings(values)
        if _label_is_evidenced_in_text(value, cleaned_text)
    ]


ADMINISTRATION_TERMS = (
    "administration",
    "administratif",
    "administrative",
    "assistante de bureau",
    "assistant de bureau",
    "secrétariat",
    "secretariat",
    "bureau",
    "classement",
    "archivage",
    "courriers",
    "documents internes",
    "suivi administratif",
)

CUSTOMER_SUPPORT_TERMS = (
    "centre d'appel",
    "call center",
    "hotline",
    "service client",
    "support client",
    "customer support",
    "réclamation client",
    "reclamation client",
    "satisfaction client",
)


def _has_any_phrase(cleaned_text: str, phrases: tuple[str, ...]) -> bool:
    text = _normalized_search_text(cleaned_text)
    return any(_normalized_search_text(phrase).strip() in text for phrase in phrases)


def _validated_resume_business_families(payload: dict[str, Any], cleaned_text: str) -> tuple[list[str], float]:
    business_families = sorted(normalize_family_set(payload.get("business_families")) - {"other"})
    family_confidence = _safe_confidence(payload.get("family_confidence"))
    role_domain_text = " ".join(
        _dedupe_strings(
            payload.get("canonical_role"),
            payload.get("target_roles"),
            payload.get("domains"),
            payload.get("responsibilities"),
            payload.get("evidence"),
        )
    )
    combined_text = f"{cleaned_text} {role_domain_text}"

    if _has_any_phrase(combined_text, ADMINISTRATION_TERMS):
        return ["administration"], max(family_confidence, 0.85)
    if business_families == ["customer_support"] and not _has_any_phrase(combined_text, CUSTOMER_SUPPORT_TERMS):
        return [], 0.0
    if not business_families or family_confidence < 0.75:
        return [], family_confidence
    return business_families, family_confidence


def _llm_resume_signals(cleaned_text: str) -> tuple[dict[str, Any], list[str]]:
    warnings = []
    if not _resume_llm_enabled():
        return {}, warnings
    try:
        # Lazy import to avoid circular dependency
        from ai.llm.enrichment import enrich_resume_text as enrich_resume_text_with_llm
        result = enrich_resume_text_with_llm(cleaned_text)
    except Exception as exc:  # noqa: BLE001 - LLM enrichment must not break CV storage
        logger.warning("resume LLM family enrichment failed: %s", _safe_error(exc))
        return {}, [f"llm_resume_enrichment_failed:{_safe_error(exc)}"]

    payload = result.as_dict()
    business_families, family_confidence = _validated_resume_business_families(payload, cleaned_text)

    return {
        "payload": payload,
        "skills": _filter_evidenced_llm_labels(payload.get("skills"), cleaned_text),
        "domains": payload.get("domains") or [],
        "tools": _filter_evidenced_llm_labels(payload.get("tools"), cleaned_text),
        "business_families": business_families,
        "family_confidence": family_confidence,
        "canonical_role": str(payload.get("canonical_role") or "").strip(),
        "target_roles": payload.get("target_roles") or [],
        "confidence": _safe_confidence(payload.get("confidence")),
    }, warnings


def _resume_raw_candidate_records_from_storage(resume: Any) -> list[SkillCandidate]:
    metadata = getattr(resume, "semantic_resume_metadata", {}) or {}
    raw_entries = metadata.get("raw_candidates", [])
    candidates: list[SkillCandidate] = []
    if isinstance(raw_entries, list):
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            text = str(entry.get("text") or "").strip()
            if not text:
                continue
            candidates.append(
                SkillCandidate(
                    text=text,
                    source=str(entry.get("source") or "stored").strip() or "stored",
                    confidence=float(entry.get("confidence") or 0.0),
                    start=entry.get("start"),
                    end=entry.get("end"),
                )
            )
    if candidates:
        return candidates

    return [
        SkillCandidate(text=text, source="stored", confidence=0.0)
        for text in clean_skill_storage_list(getattr(resume, "extracted_raw_skills", []))
    ]


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
    filtered_candidates, rejected_candidates = filter_resume_skill_candidates(candidates)
    mapped = map_to_esco(
        [candidate.text for candidate in filtered_candidates],
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
        candidates=filtered_candidates,
        mapped_count=len(mapped),
        text_length=len(cleaned),
        language_count=len(languages),
    )
    warnings = []
    if rejected_candidates:
        warnings.append("resume_candidate_quality_filter_rejected_candidates")
    if time.monotonic() - started > 20.0:
        warnings.append("semantic_processing_exceeded_target_runtime")
    llm_signals, llm_warnings = _llm_resume_signals(cleaned)
    warnings.extend(llm_warnings)
    llm_payload = llm_signals.get("payload") if llm_signals else {}
    business_families = llm_signals.get("business_families", []) if llm_signals else []
    family_confidence = llm_signals.get("family_confidence", 0.0) if llm_signals else 0.0
    canonical_role = llm_signals.get("canonical_role", "") if llm_signals else ""
    target_roles = _dedupe_strings(llm_signals.get("target_roles", []) if llm_signals else [])
    semantic_confidence_value = max(
        confidence,
        float(llm_signals.get("confidence", 0.0) or 0.0) if llm_signals else 0.0,
    )

    return ResumeSemanticSignals(
        skills=_dedupe_strings(skills, llm_signals.get("skills", []) if llm_signals else []),
        domains=_dedupe_strings(domains, llm_signals.get("domains", []) if llm_signals else []),
        tools=_dedupe_strings(tools, llm_signals.get("tools", []) if llm_signals else []),
        business_families=business_families,
        family_confidence=family_confidence,
        canonical_role=canonical_role,
        target_roles=target_roles,
        languages_detected=languages,
        semantic_confidence=semantic_confidence_value,
        llm_enrichment=llm_payload if isinstance(llm_payload, dict) else {},
        raw_candidates=filtered_candidates,
        rejected_candidates=rejected_candidates,
        mapped_candidates=mapped,
        warnings=warnings,
    )


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

    extracted_raw_skills = _raw_skill_candidates(signals)
    normalization_error = ""
    try:
        normalization_payload = build_skill_normalization_payload(extracted_raw_skills)
    except Exception as exc:  # noqa: BLE001 - must not break semantic resume storage
        normalization_error = safe_normalization_error(exc)
        logger.exception(
            "resume ESCO skill normalization failed resume_id=%s",
            getattr(resume, "pk", None),
        )
        normalization_payload = SkillNormalizationStoragePayload(
            raw_skills=extracted_raw_skills,
            normalized_skills=[],
            content_hash=build_skill_storage_hash(extracted_raw_skills),
        )

    with transaction.atomic():
        resume.extracted_skills = signals.skills
        resume.extracted_raw_skills = normalization_payload.raw_skills
        resume.extracted_normalized_skills = normalization_payload.normalized_skills
        resume.extracted_skills_normalization_hash = normalization_payload.content_hash
        resume.extracted_skills_normalization_updated_at = timezone.now()
        resume.extracted_skills_normalization_error = normalization_error
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
            "rejected_raw_candidates": [candidate.as_dict() for candidate in signals.rejected_candidates[:80]],
            "mapped_candidates": signals.mapped_candidates[:40],
            "candidate_quality": _resume_candidate_quality_metadata(signals),
            "business_families": signals.business_families,
            "family_confidence": round(float(signals.family_confidence or 0.0), 4),
            "canonical_role": signals.canonical_role,
            "target_roles": signals.target_roles,
            "llm_enrichment": signals.llm_enrichment,
            "warnings": signals.warnings,
        }
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

    summary = summarize_normalized_skill_entries(normalization_payload.normalized_skills)
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
        "normalized_skills_count": len(normalization_payload.normalized_skills),
        "matched_count": summary.matched_entries,
        "unmatched_count": summary.unmatched_entries,
        "official_matches": summary.official_matches,
        "legacy_matches": summary.legacy_matches,
        "rejected_candidates_count": len(signals.rejected_candidates),
    }


def refresh_resume_skill_normalization_from_existing_candidates(
    resume: Any,
    *,
    force: bool = False,
) -> dict[str, Any]:
    stored_candidates = _resume_raw_candidate_records_from_storage(resume)
    filtered_candidates, rejected_candidates = filter_resume_skill_candidates(stored_candidates)
    filtered_raw_skills = [candidate.text for candidate in filtered_candidates]
    content_hash = build_skill_storage_hash(filtered_raw_skills)

    metadata = getattr(resume, "semantic_resume_metadata", {}) or {}
    candidate_quality = metadata.get("candidate_quality", {}) if isinstance(metadata, dict) else {}
    current_quality_version = str(candidate_quality.get("candidate_quality_version") or "").strip()

    if (
        not force
        and getattr(resume, "extracted_skills_normalization_hash", "") == content_hash
        and getattr(resume, "extracted_skills_normalization_updated_at", None)
        and current_quality_version == RESUME_CANDIDATE_QUALITY_VERSION
    ):
        return {
            "status": SEMANTIC_STATUS_SKIPPED,
            "reason": "fresh_candidate_cleanup",
            "resume_id": getattr(resume, "pk", None),
        }

    normalization_error = ""
    try:
        normalization_payload = build_skill_normalization_payload(filtered_raw_skills)
    except Exception as exc:  # noqa: BLE001 - fail-soft for bulk cleanup
        normalization_error = safe_normalization_error(exc)
        logger.exception(
            "resume ESCO candidate cleanup normalization failed resume_id=%s",
            getattr(resume, "pk", None),
        )
        normalization_payload = SkillNormalizationStoragePayload(
            raw_skills=filtered_raw_skills,
            normalized_skills=[],
            content_hash=content_hash,
        )

    with transaction.atomic():
        resume.extracted_raw_skills = normalization_payload.raw_skills
        resume.extracted_normalized_skills = normalization_payload.normalized_skills
        resume.extracted_skills_normalization_hash = normalization_payload.content_hash
        resume.extracted_skills_normalization_updated_at = timezone.now()
        resume.extracted_skills_normalization_error = normalization_error
        resume.semantic_resume_metadata = {
            **(metadata if isinstance(metadata, dict) else {}),
            "raw_candidates": [candidate.as_dict() for candidate in filtered_candidates[:40]],
            "rejected_raw_candidates": [candidate.as_dict() for candidate in rejected_candidates[:80]],
            "candidate_quality": {
                **_resume_candidate_quality_metadata(
                    ResumeSemanticSignals(
                        raw_candidates=filtered_candidates,
                        rejected_candidates=rejected_candidates,
                    )
                ),
            },
        }
        resume.save(
            update_fields=[
                "extracted_raw_skills",
                "extracted_normalized_skills",
                "extracted_skills_normalization_hash",
                "extracted_skills_normalization_updated_at",
                "extracted_skills_normalization_error",
                "semantic_resume_metadata",
            ]
        )

    summary = summarize_normalized_skill_entries(normalization_payload.normalized_skills)
    return {
        "status": "updated",
        "resume_id": getattr(resume, "pk", None),
        "normalized_skills_count": len(normalization_payload.normalized_skills),
        "matched_count": summary.matched_entries,
        "unmatched_count": summary.unmatched_entries,
        "official_matches": summary.official_matches,
        "legacy_matches": summary.legacy_matches,
        "rejected_candidates_count": len(rejected_candidates),
    }
