from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from ai.tasks import (
    SkillNormalizationStoragePayload,
    build_skill_normalization_payload,
    build_skill_storage_hash,
    clean_skill_storage_list,
    safe_normalization_error,
)
from opportunities.models import Opportunite

from .enrichment import enrich_opportunity_text
from .opportunity_post_validation import post_validate_opportunity_enrichment
from .providers import LLMProvider
from .schemas import LLMExtractionResult


logger = logging.getLogger(__name__)

LLM_OPPORTUNITY_ENRICHMENT_VERSION = "gemini-opportunity-enrichment-v3"
MIN_CONFIDENCE_TO_APPLY = 0.75
MAX_APPLIED_SKILLS = 18
LLM_CANONICAL_EXTRACTION_SOURCES = {"gemini", "ollama", "fallback"}
LOW_SIGNAL_SKILL_KEYS = {
    "administration",
    "administrative",
    "analyse",
    "analysis",
    "coordination",
    "delivery",
    "employee",
    "hygiene",
    "integration",
    "management",
    "platform",
    "quality",
    "reporting",
}


def _normalize_key(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _content_hash(opportunity: Opportunite) -> str:
    payload = "\n".join(
        [
            str(getattr(opportunity, "titre", "") or ""),
            str(getattr(opportunity, "description", "") or ""),
            ",".join(clean_skill_storage_list(getattr(opportunity, "skills", []))),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def opportunity_needs_llm_enrichment(opportunity: Opportunite) -> bool:
    skills = clean_skill_storage_list(getattr(opportunity, "skills", []))
    if len(skills) <= 1:
        return True
    skill_keys = {_normalize_key(skill) for skill in skills}
    return len(skill_keys) <= 5 and skill_keys.issubset(LOW_SIGNAL_SKILL_KEYS)


def _source_text_for_validation(opportunity: Opportunite) -> str:
    parts = [
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
        " ".join(clean_skill_storage_list(getattr(opportunity, "skills", []))),
    ]
    return " ".join(str(part or "") for part in parts).casefold()


def _clean_llm_skill_label(label: str, *, source_text: str, language_keys: set[str] | None = None) -> str:
    value = str(label or "").strip()
    if not value:
        return ""

    # Small local models sometimes expand acronyms even when the source only
    # contains the acronym. Keep the explicit acronym and drop invented prose.
    if "(" in value and ")" in value:
        prefix = value.split("(", 1)[0].strip(" -:;,.")
        parenthetical = value.split("(", 1)[1].rsplit(")", 1)[0].strip()
        prefix_is_acronym = prefix.isupper() and 2 <= len(prefix) <= 12
        if prefix_is_acronym or (parenthetical and parenthetical.casefold() not in source_text):
            value = prefix

    key = _normalize_key(value)
    if key in (language_keys or set()):
        return ""

    return value.strip(" -:;,.")


def _fallback_canonical_role(result: LLMExtractionResult, opportunity: Opportunite) -> str:
    if result.canonical_role:
        return result.canonical_role
    if result.target_roles:
        return result.target_roles[0]
    return str(getattr(opportunity, "titre", "") or "").strip()[:80]


def _family_evidence_text(result: LLMExtractionResult, opportunity: Opportunite) -> str:
    values = [
        getattr(opportunity, "titre", ""),
        result.canonical_role,
        *result.target_roles,
        *result.skills,
        *result.tools,
        *result.soft_skills,
        *result.domains,
        *result.responsibilities,
        *result.requirements,
    ]
    extra_data = getattr(opportunity, "extra_data", None)
    if isinstance(extra_data, dict):
        values.extend(
            [
                extra_data.get("company_sector"),
                extra_data.get("sector"),
                extra_data.get("industry"),
            ]
        )
    return " ".join(str(value or "") for value in values).casefold()


def _validated_business_families(result: LLMExtractionResult, opportunity: Opportunite) -> tuple[list[str], float, list[str]]:
    families = []
    seen = set()
    for family in result.business_families:
        if family in seen:
            continue
        seen.add(family)
        families.append(family)

    warnings = list(result.warnings)
    family_confidence = float(result.family_confidence or 0.0)
    if not families:
        return ["other"], 0.0, [*warnings, "missing_llm_family"]
    if len(families) > 1 and "other" in families:
        families = [family for family in families if family != "other"]
        family_confidence = min(family_confidence, 0.75)
    return families or ["other"], family_confidence, warnings



def _candidate_skill_labels(result: LLMExtractionResult, opportunity: Opportunite) -> list[str]:
    source_text = _source_text_for_validation(opportunity)
    language_keys = {_normalize_key(label) for label in result.languages}
    labels = []
    for label in [*result.skills, *result.tools]:
        cleaned = _clean_llm_skill_label(label, source_text=source_text, language_keys=language_keys)
        if cleaned:
            labels.append(cleaned)
    return clean_skill_storage_list(labels)[:MAX_APPLIED_SKILLS]


def _extraction_quality_score(result: LLMExtractionResult, extracted_skills: list[str]) -> int:
    """Score structure richness without hardcoding individual skills."""
    score = 0
    if _normalize_key(result.canonical_role):
        score += 2
    if result.target_roles:
        score += 1
    if len(extracted_skills) >= 2:
        score += 2
    elif len(extracted_skills) == 1:
        score += 1
    if result.domains:
        score += 1
    if result.soft_skills:
        score += 1
    if result.responsibilities:
        score += 2
    if result.requirements:
        score += 2
    if result.evidence:
        score += 1
    if result.experience_level or result.years_experience is not None:
        score += 1
    if result.contract_types or result.work_modes or result.locations:
        score += 1
    return score


def _should_apply_extracted_skills(
    *,
    result: LLMExtractionResult,
    extracted_skills: list[str],
    apply_skills: bool,
    min_confidence: float,
) -> bool:
    if not apply_skills or result.confidence < min_confidence or not extracted_skills:
        return False
    return _extraction_quality_score(result, extracted_skills) >= 4


def _has_actionable_skill_support(result: LLMExtractionResult, extracted_skills: list[str]) -> bool:
    """Avoid replacing skills with soft-trait-only labels.

    The LLM enrichment itself is still stored and used by JobBERT. This gate
    only decides whether the public/opportunity skill list should be replaced.
    """
    if len(extracted_skills) >= 2:
        return True
    if len(extracted_skills) >= 1 and (result.tools or result.domains):
        return True
    if result.tools and (result.domains or result.responsibilities):
        return True
    return False


def _build_llm_metadata(
    result: LLMExtractionResult,
    *,
    opportunity: Opportunite,
    content_hash: str,
    applied: bool,
    replaced_previous_skills: bool,
    previous_skills: list[str],
) -> dict[str, Any]:
    business_families, family_confidence, warnings = _validated_business_families(result, opportunity)
    return {
        "version": LLM_OPPORTUNITY_ENRICHMENT_VERSION,
        "provider": result.provider,
        "model": result.model,
        "content_hash": content_hash,
        "updated_at": timezone.now().isoformat(),
        "applied_to_skills": applied,
        "skills_source": "llm" if applied else "not_applied",
        "replaced_previous_skills": replaced_previous_skills,
        "previous_skills": previous_skills[:MAX_APPLIED_SKILLS],
        "confidence": round(float(result.confidence or 0.0), 4),
        "target_roles": result.target_roles,
        "canonical_role": _fallback_canonical_role(result, opportunity),
        "skills": result.skills,
        "tools": result.tools,
        "soft_skills": result.soft_skills,
        "domains": result.domains,
        "business_families": business_families,
        "family_confidence": round(float(family_confidence or 0.0), 4),
        "seniority": result.seniority,
        "experience_level": result.experience_level,
        "years_experience": result.years_experience,
        "years_experience_min": result.years_experience_min,
        "years_experience_max": result.years_experience_max,
        "languages": result.languages,
        "contract_types": result.contract_types,
        "work_modes": result.work_modes,
        "locations": result.locations,
        "salary": result.salary,
        "education_level": result.education_level,
        "responsibilities": result.responsibilities,
        "requirements": result.requirements,
        "evidence": result.evidence,
        "warnings": warnings,
    }


def _normalize_applied_skills(applied_skills: list[str]) -> tuple[SkillNormalizationStoragePayload, str]:
    content_hash = build_skill_storage_hash(applied_skills)
    try:
        return build_skill_normalization_payload(applied_skills), ""
    except Exception as exc:  # noqa: BLE001 - LLM enrichment must fail soft
        logger.exception("LLM opportunity skill storage failed")
        return (
            SkillNormalizationStoragePayload(
                raw_skills=applied_skills,
                normalized_skills=[],
                content_hash=content_hash,
            ),
            safe_normalization_error(exc),
        )


def enrich_opportunity_with_llm(
    opportunity_id: int,
    *,
    provider: LLMProvider | None = None,
    force: bool = False,
    apply_skills: bool = True,
    min_confidence: float = MIN_CONFIDENCE_TO_APPLY,
) -> dict[str, Any]:
    try:
        opportunity = Opportunite.objects.only(
            "id",
            "titre",
            "description",
            "description_html",
            "organisation_nom",
            "ville",
            "contract_type",
            "availability",
            "experience_min",
            "experience_max",
            "experience_years",
            "education_level",
            "normalized_work_mode",
            "salary",
            "skills",
            "raw_skills",
            "normalized_skills",
            "skills_normalization_hash",
            "skills_normalization_updated_at",
            "skills_normalization_error",
            "languages_fallback",
            "extra_data",
            "source",
        ).get(pk=int(opportunity_id))
    except (TypeError, ValueError):
        return {"status": "skipped", "reason": "invalid_opportunity_id"}
    except Opportunite.DoesNotExist:
        return {"status": "skipped", "reason": "missing_opportunity", "opportunity_id": opportunity_id}

    current_hash = _content_hash(opportunity)
    previous_skills = clean_skill_storage_list(getattr(opportunity, "skills", []))
    extra_data = getattr(opportunity, "extra_data", {}) or {}
    if not isinstance(extra_data, dict):
        extra_data = {}
    previous = extra_data.get("llm_enrichment")
    if (
        not force
        and isinstance(previous, dict)
        and previous.get("version") == LLM_OPPORTUNITY_ENRICHMENT_VERSION
        and previous.get("content_hash") == current_hash
    ):
        return {"status": "skipped", "reason": "fresh", "opportunity_id": opportunity.pk}

    result = post_validate_opportunity_enrichment(
        enrich_opportunity_text(opportunity, provider=provider),
        opportunity,
    )
    extracted_skills = _candidate_skill_labels(result, opportunity)
    should_apply = _should_apply_extracted_skills(
        result=result,
        extracted_skills=extracted_skills,
        apply_skills=apply_skills,
        min_confidence=min_confidence,
    )
    replaced_previous_skills = should_apply and previous_skills != extracted_skills

    normalization_payload = None
    normalization_error = ""
    if should_apply:
        normalization_payload, normalization_error = _normalize_applied_skills(extracted_skills)
        if not _has_actionable_skill_support(result, normalization_payload.raw_skills):
            should_apply = False
            replaced_previous_skills = False
            normalization_payload = None

    with transaction.atomic():
        locked = Opportunite.objects.select_for_update().get(pk=opportunity.pk)
        locked_extra_data = getattr(locked, "extra_data", {}) or {}
        if not isinstance(locked_extra_data, dict):
            locked_extra_data = {}

        update_fields = ["extra_data", "date_modification"]
        locked_extra_data = {
            **locked_extra_data,
            "llm_enrichment": _build_llm_metadata(
                result,
                opportunity=opportunity,
                content_hash=current_hash,
                applied=should_apply,
                replaced_previous_skills=replaced_previous_skills,
                previous_skills=previous_skills,
            ),
        }
        locked.extra_data = locked_extra_data

        if should_apply and normalization_payload is not None:
            if clean_skill_storage_list(getattr(locked, "skills", [])) != normalization_payload.raw_skills:
                locked.skills = normalization_payload.raw_skills
                update_fields.append("skills")
            if clean_skill_storage_list(getattr(locked, "raw_skills", [])) != normalization_payload.raw_skills:
                locked.raw_skills = normalization_payload.raw_skills
                update_fields.append("raw_skills")
            if list(getattr(locked, "normalized_skills", []) or []) != normalization_payload.normalized_skills:
                locked.normalized_skills = normalization_payload.normalized_skills
                update_fields.append("normalized_skills")
            if getattr(locked, "skills_normalization_hash", "") != normalization_payload.content_hash:
                locked.skills_normalization_hash = normalization_payload.content_hash
                update_fields.append("skills_normalization_hash")
            if getattr(locked, "skills_normalization_error", "") != normalization_error:
                locked.skills_normalization_error = normalization_error
                update_fields.append("skills_normalization_error")
            locked.skills_normalization_updated_at = timezone.now()
            update_fields.append("skills_normalization_updated_at")

        if result.years_experience_min is not None and getattr(locked, "experience_min", None) is None:
            locked.experience_min = result.years_experience_min
            update_fields.append("experience_min")
        if result.years_experience_max is not None and getattr(locked, "experience_max", None) is None:
            locked.experience_max = result.years_experience_max
            update_fields.append("experience_max")
        if result.education_level and not getattr(locked, "education_level", ""):
            locked.education_level = result.education_level[:120]
            update_fields.append("education_level")
        if result.salary and not getattr(locked, "salary", ""):
            locked.salary = result.salary[:120]
            update_fields.append("salary")
        if result.contract_types and not getattr(locked, "contract_type", ""):
            locked.contract_type = result.contract_types[0][:64]
            update_fields.append("contract_type")
        if result.work_modes and not getattr(locked, "availability", ""):
            locked.availability = result.work_modes[0][:120]
            update_fields.append("availability")
        if result.locations and not getattr(locked, "ville", ""):
            locked.ville = result.locations[0][:120]
            update_fields.append("ville")

        locked.save(update_fields=sorted(set(update_fields)))

    business_families, family_confidence, _warnings = _validated_business_families(result, opportunity)
    return {
        "status": "updated",
        "opportunity_id": opportunity.pk,
        "applied_to_skills": should_apply,
        "confidence": result.confidence,
        "skills": extracted_skills,
        "business_families": business_families,
        "family_confidence": family_confidence,
        "canonical_role": _fallback_canonical_role(result, opportunity),
        "experience_level": result.experience_level,
        "years_experience": result.years_experience,
        "domains": result.domains,
        "soft_skills": result.soft_skills,
        "responsibilities": result.responsibilities,
        "requirements": result.requirements,
        "normalized_skills_count": len(normalization_payload.normalized_skills) if normalization_payload else 0,
        "normalization_error": normalization_error,
    }
