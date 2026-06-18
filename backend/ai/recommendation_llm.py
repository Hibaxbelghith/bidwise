from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

from ai.hierarchy_llm import (
    LLMHierarchyValidation,
    build_hierarchy_validation_cache_key,
    build_opportunity_content_hash,
    get_cached_hierarchy_decision,
    store_hierarchy_decision,
    validate_hierarchy_with_llm,
)
from ai.llm.providers import LLMProviderError, LLMProviderUnavailable, LLMTransientProviderError
from ai.quality_gates import (
    BUCKET_STRONG_MATCH,
    annotate_recommendation_quality,
    build_recommendation_evidence,
    classify_recommendation_bucket,
)


logger = logging.getLogger(__name__)

LLM_MIN_CONFIDENCE = 0.65
LLM_VALIDATION_MIN_SCORE = 0.60


def recommendation_llm_hierarchy_enabled() -> bool:
    return bool(getattr(settings, "RECOMMENDATION_LLM_HIERARCHY_ENABLED", False))


def recommendation_llm_top_n() -> int:
    return max(1, int(getattr(settings, "RECOMMENDATION_LLM_HIERARCHY_TOP_N", 10) or 10))


def recommendation_llm_min_score() -> float:
    return max(
        0.0,
        min(
            float(getattr(settings, "RECOMMENDATION_LLM_HIERARCHY_MIN_SCORE", LLM_VALIDATION_MIN_SCORE) or 0.0),
            1.0,
        ),
    )


def should_validate_llm_hierarchy(
    opportunity,
    bucket: str,
    *,
    min_score: float | None = None,
) -> bool:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
    if not isinstance(validation, dict) or not validation.get("needs_llm"):
        return False
    threshold = recommendation_llm_min_score() if min_score is None else min_score
    return bucket == BUCKET_STRONG_MATCH or _safe_float(getattr(opportunity, "match_score", 0.0)) >= threshold


def apply_llm_hierarchy_validation_to_ranked(
    ranked: list[Any],
    *,
    features: dict[str, Any],
    profile_text: str,
    profile_strength: dict[str, Any] | None = None,
    top_n: int | None = None,
    min_score: float | None = None,
    cache_only: bool = False,
) -> dict[str, int]:
    if not recommendation_llm_hierarchy_enabled():
        return {"eligible": 0, "validated": 0, "errors": 0}

    effective_top_n = recommendation_llm_top_n() if top_n is None else max(1, int(top_n))
    effective_min_score = recommendation_llm_min_score() if min_score is None else min_score
    stats = {"eligible": 0, "validated": 0, "errors": 0, "cache_misses": 0}

    for opportunity in list(ranked)[:effective_top_n]:
        evidence = build_recommendation_evidence(features, opportunity, profile_strength)
        bucket, _bucket_reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )
        if not should_validate_llm_hierarchy(opportunity, bucket, min_score=effective_min_score):
            continue

        stats["eligible"] += 1
        try:
            result = _validate_hierarchy_with_cache(
                profile_text=profile_text,
                opportunity=opportunity,
                cache_only=cache_only,
            )
        except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
            stats["errors"] += 1
            _record_llm_error(opportunity, exc)
            continue
        if result is None:
            stats["cache_misses"] += 1
            continue

        _apply_llm_hierarchy_result(opportunity, result, features=features)
        annotate_recommendation_quality(
            opportunity,
            features=features,
            profile_strength=profile_strength,
        )
        stats["validated"] += 1

    return stats


def _validate_hierarchy_with_cache(
    *,
    profile_text: str,
    opportunity,
    cache_only: bool = False,
) -> LLMHierarchyValidation | None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
    opportunity_skills = _opportunity_skills(opportunity)
    content_hash = build_opportunity_content_hash(
        opportunity_title=str(getattr(opportunity, "titre", "") or ""),
        opportunity_description=str(getattr(opportunity, "description", "") or ""),
        opportunity_skills=opportunity_skills,
    )
    cache_key = build_hierarchy_validation_cache_key(
        profile_text=profile_text,
        opportunity_id=getattr(opportunity, "id", ""),
        hierarchy_validation=validation,
        opportunity_content_hash=content_hash,
    )
    cached = get_cached_hierarchy_decision(cache_key)
    if cached is not None:
        _record_cache_hit(opportunity)
        return cached
    if cache_only:
        _record_cache_miss(opportunity)
        return None

    result = validate_hierarchy_with_llm(
        profile_text=profile_text,
        opportunity_id=getattr(opportunity, "id", ""),
        opportunity_title=str(getattr(opportunity, "titre", "") or ""),
        opportunity_description=str(getattr(opportunity, "description", "") or ""),
        opportunity_skills=opportunity_skills,
        hierarchy_validation=validation,
    )
    store_hierarchy_decision(
        cache_key=cache_key,
        profile_text=profile_text,
        opportunity_id=getattr(opportunity, "id", ""),
        opportunity_content_hash=content_hash,
        hierarchy_validation=validation,
        result=result,
    )
    return result


def _apply_llm_hierarchy_result(
    opportunity,
    result: LLMHierarchyValidation,
    *,
    features: dict[str, Any] | None = None,
) -> None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    if not isinstance(debug, dict):
        debug = {}
    validation = dict(debug.get("hierarchy_validation") or {})
    debug["llm_hierarchy_validation"] = result.as_dict()
    debug["llm_hierarchy_policy"] = {
        "applied": False,
        "overridden_by_exact_evidence": False,
        "kept_for_review": False,
        "reason": "",
    }

    if _exact_match_should_survive_llm_review(
        features=features,
        opportunity=opportunity,
        result=result,
    ):
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = "none"
        validation["score_multiplier"] = 1.0
        validation["reason"] = "Exact role and skill evidence override weak LLM hierarchy concern"
        debug["llm_hierarchy_policy"] = {
            "applied": False,
            "overridden_by_exact_evidence": True,
            "kept_for_review": False,
            "reason": validation["reason"],
        }
    elif (
        result.confidence < LLM_MIN_CONFIDENCE
        or result.issue == "unclear"
        or (not result.is_compatible and not _llm_issue_has_explicit_opportunity_support(validation, result))
    ):
        validation["needs_llm"] = True
        validation["hierarchy_issue"] = "none"
        validation["reason"] = result.reason or "LLM hierarchy validation remains unsupported by explicit terms"
        debug["llm_hierarchy_policy"] = {
            "applied": False,
            "overridden_by_exact_evidence": False,
            "kept_for_review": True,
            "reason": validation["reason"],
        }
    elif result.is_compatible:
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = "none"
        validation["score_multiplier"] = 1.0
        validation["reason"] = result.reason or "LLM confirmed hierarchy compatibility"
        debug["llm_hierarchy_policy"] = {
            "applied": True,
            "overridden_by_exact_evidence": False,
            "kept_for_review": False,
            "reason": validation["reason"],
        }
    else:
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = result.issue
        validation["score_multiplier"] = min(float(validation.get("score_multiplier") or 1.0), 0.68)
        validation["reason"] = result.reason or "LLM rejected hierarchy compatibility"
        debug["llm_hierarchy_policy"] = {
            "applied": True,
            "overridden_by_exact_evidence": False,
            "kept_for_review": False,
            "reason": validation["reason"],
        }

    debug["hierarchy_validation"] = validation
    setattr(opportunity, "recommendation_debug", debug)


def _llm_issue_has_explicit_opportunity_support(
    validation: dict[str, Any],
    result: LLMHierarchyValidation,
) -> bool:
    opportunity_signal = validation.get("opportunity_signal") or {}
    if not isinstance(opportunity_signal, dict):
        opportunity_signal = {}

    if result.issue == "seniority_gap":
        return bool(opportunity_signal.get("seniority_terms"))
    if result.issue == "responsibility_gap":
        return bool(opportunity_signal.get("responsibility_terms"))
    if result.issue in {"qualification_gap", "overqualified_scope"}:
        return bool(opportunity_signal.get("qualification_terms"))
    return result.issue not in {"none", "unclear"}


def _exact_match_should_survive_llm_review(
    *,
    features: dict[str, Any] | None,
    opportunity,
    result: LLMHierarchyValidation,
) -> bool:
    if result.is_compatible or result.issue not in {"seniority_gap", "responsibility_gap"}:
        return False
    evidence = build_recommendation_evidence(features or {}, opportunity)
    return bool(
        evidence.get("role_match")
        and int(evidence.get("skill_overlap") or 0) >= 2
        and _safe_float(getattr(opportunity, "match_score", 0.0)) >= 0.75
    )


def _record_llm_error(opportunity, exc: Exception) -> None:
    logger.info(
        "Recommendation LLM hierarchy validation skipped opportunity_id=%s error=%s",
        getattr(opportunity, "id", None),
        exc.__class__.__name__,
    )
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    if isinstance(debug, dict):
        debug["llm_hierarchy_validation_error"] = exc.__class__.__name__
        setattr(opportunity, "recommendation_debug", debug)


def _record_cache_hit(opportunity) -> None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    if isinstance(debug, dict):
        debug["llm_hierarchy_cache_hit"] = True
        setattr(opportunity, "recommendation_debug", debug)


def _record_cache_miss(opportunity) -> None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    if isinstance(debug, dict):
        debug["llm_hierarchy_cache_hit"] = False
        debug["llm_hierarchy_cache_only_miss"] = True
        setattr(opportunity, "recommendation_debug", debug)


def _opportunity_skills(opportunity) -> list[str]:
    skills = getattr(opportunity, "skills", None) or []
    if isinstance(skills, list):
        return [str(skill).strip() for skill in skills if str(skill or "").strip()]
    return []


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0
