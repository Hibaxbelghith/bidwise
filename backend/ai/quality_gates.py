from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opportunities.normalization.text import normalize_lookup_key
from .profile_strength import recommendation_mode_for_profile
from .recommendation_service import _clean_list, _get_value


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

SEMANTIC_STRONG = "STRONG"
SEMANTIC_MEDIUM = "MEDIUM"
SEMANTIC_WEAK = "WEAK"

MAX_QUALITY_REASONS = 5
MAX_QUALITY_GAPS = 3
GENERIC_REASON_LABELS = {
    "experience match",
    "remote match",
    "hybrid match",
    "on-site preference",
}
GENERIC_SINGLE_WORD_REASONS = {
    "ai",
    "healthcare",
    "fintech",
    "ecommerce",
    "education",
    "tourism",
    "saas",
    "cybersecurity",
    "industry",
    "telecom",
    "python",
    "javascript",
    "typescript",
    "react",
    "django",
    "sql",
    "css",
}


@dataclass(frozen=True)
class QualityThresholds:
    min_score: float
    min_exact_evidence_score: float
    semantic_only: float
    resume_semantic: float
    industry_semantic: float
    medium_semantic: float
    strong_semantic: float


QUALITY_THRESHOLDS = {
    "LOW": QualityThresholds(
        min_score=0.35,
        min_exact_evidence_score=0.30,
        semantic_only=0.60,
        resume_semantic=0.58,
        industry_semantic=0.52,
        medium_semantic=0.50,
        strong_semantic=0.60,
    ),
    "MEDIUM": QualityThresholds(
        min_score=0.40,
        min_exact_evidence_score=0.30,
        semantic_only=0.55,
        resume_semantic=0.52,
        industry_semantic=0.48,
        medium_semantic=0.48,
        strong_semantic=0.62,
    ),
    "HIGH": QualityThresholds(
        min_score=0.35,
        min_exact_evidence_score=0.28,
        semantic_only=0.45,
        resume_semantic=0.50,
        industry_semantic=0.45,
        medium_semantic=0.45,
        strong_semantic=0.65,
    ),
}


def _thresholds(profile_strength: dict[str, Any] | None) -> QualityThresholds:
    level = str((profile_strength or {}).get("level") or "LOW").upper()
    return QUALITY_THRESHOLDS.get(level, QUALITY_THRESHOLDS["LOW"])


def _as_normalized_map(values: Any) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for value in _clean_list(values):
        key = normalize_lookup_key(value)
        if key and key not in mapped:
            mapped[key] = str(value).strip()
    return mapped


def _token_set(value: Any) -> set[str]:
    return {
        token
        for token in normalize_lookup_key(value).split()
        if len(token) >= 3
    }


def _semantic_score(opportunity: Any) -> float:
    try:
        return max(0.0, min(1.0, float(_get_value(opportunity, "semantic_score", 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _match_score(opportunity: Any) -> float:
    try:
        return max(0.0, min(1.0, float(_get_value(opportunity, "match_score", 0.0) or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _semantic_strength(score: float, thresholds: QualityThresholds) -> str:
    if score >= thresholds.strong_semantic:
        return SEMANTIC_STRONG
    if score >= thresholds.medium_semantic:
        return SEMANTIC_MEDIUM
    return SEMANTIC_WEAK


def _skill_overlap(features: dict[str, Any], opportunity: Any) -> tuple[list[str], int]:
    user_skills = _as_normalized_map(features.get("skills"))
    opportunity_skills = _as_normalized_map(_get_value(opportunity, "skills", []))
    title = normalize_lookup_key(_get_value(opportunity, "titre", ""))

    matched: list[str] = []
    seen = set()
    for key, label in user_skills.items():
        if key in opportunity_skills or (key and key in title):
            if key not in seen:
                seen.add(key)
                matched.append(label)
    return matched, len(matched)


def _role_match(features: dict[str, Any], opportunity: Any) -> tuple[bool, list[str]]:
    title = normalize_lookup_key(_get_value(opportunity, "titre", ""))
    if not title:
        return False, []

    matched = []
    for role in _clean_list(features.get("target_roles")) or _clean_list(features.get("roles")):
        normalized_role = normalize_lookup_key(role)
        if normalized_role and normalized_role in title:
            matched.append(str(role).strip())
    return bool(matched), matched[:2]


def _title_token_overlap(features: dict[str, Any], opportunity: Any) -> bool:
    title_tokens = _token_set(_get_value(opportunity, "titre", ""))
    if not title_tokens:
        return False
    profile_terms = []
    profile_terms.extend(_clean_list(features.get("target_roles")))
    profile_terms.extend(_clean_list(features.get("roles")))
    profile_terms.extend(_clean_list(features.get("skills")))
    profile_tokens = set()
    for term in profile_terms:
        profile_tokens.update(_token_set(term))
    return len(profile_tokens.intersection(title_tokens)) >= 2


def _industry_match(features: dict[str, Any], opportunity: Any) -> bool:
    interests = set(_as_normalized_map(features.get("interests")).keys())
    industries = set(_as_normalized_map(_get_value(opportunity, "normalized_industries", [])).keys())
    return bool(interests and industries and interests.intersection(industries))


def build_recommendation_evidence(
    features: dict[str, Any] | None,
    opportunity: Any,
    profile_strength: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = features if isinstance(features, dict) else {}
    thresholds = _thresholds(profile_strength)
    semantic_score = _semantic_score(opportunity)
    matched_skills, skill_overlap = _skill_overlap(features, opportunity)
    role_match, matched_roles = _role_match(features, opportunity)
    title_overlap = _title_token_overlap(features, opportunity)
    industry_match = _industry_match(features, opportunity)
    resume_present = bool(str(features.get("resume_text") or "").strip())
    resume_signal = resume_present and semantic_score >= thresholds.resume_semantic
    semantic_strength = _semantic_strength(semantic_score, thresholds)
    strong_semantic = semantic_score >= thresholds.semantic_only

    strong_evidence = 0
    strong_evidence += 1 if skill_overlap else 0
    strong_evidence += 1 if role_match or title_overlap else 0
    strong_evidence += 1 if industry_match and semantic_score >= thresholds.industry_semantic else 0
    strong_evidence += 1 if resume_signal else 0
    strong_evidence += 1 if strong_semantic else 0

    return {
        "skill_overlap": skill_overlap,
        "matched_skills": matched_skills,
        "role_match": role_match,
        "matched_roles": matched_roles,
        "title_overlap": title_overlap,
        "industry_match": industry_match,
        "semantic_score": semantic_score,
        "semantic_strength": semantic_strength,
        "resume_signal": resume_signal,
        "resume_present": resume_present,
        "strong_semantic": strong_semantic,
        "strong_evidence_count": strong_evidence,
    }


def evidence_summary(evidence: dict[str, Any] | None) -> dict[str, Any]:
    evidence = evidence if isinstance(evidence, dict) else {}
    return {
        "skill_overlap": int(evidence.get("skill_overlap") or 0),
        "role_match": bool(evidence.get("role_match")),
        "title_overlap": bool(evidence.get("title_overlap")),
        "industry_match": bool(evidence.get("industry_match")),
        "semantic_strength": evidence.get("semantic_strength") or SEMANTIC_WEAK,
        "resume_signal": bool(evidence.get("resume_signal")),
    }


def passes_recommendation_quality_gate(
    *,
    features: dict[str, Any] | None,
    opportunity: Any,
    profile_strength: dict[str, Any] | None,
    evidence: dict[str, Any] | None = None,
) -> bool:
    evidence = evidence or build_recommendation_evidence(features, opportunity, profile_strength)
    thresholds = _thresholds(profile_strength)
    score = _match_score(opportunity)
    has_exact_evidence = bool(
        evidence.get("skill_overlap")
        or evidence.get("role_match")
        or evidence.get("title_overlap")
    )
    if score < thresholds.min_score and not (
        has_exact_evidence and score >= thresholds.min_exact_evidence_score
    ):
        return False

    if evidence.get("skill_overlap"):
        return True
    if evidence.get("role_match") or evidence.get("title_overlap"):
        return True
    if evidence.get("industry_match") and evidence.get("semantic_score", 0.0) >= thresholds.industry_semantic:
        return True
    if evidence.get("resume_signal"):
        return True
    if evidence.get("strong_semantic"):
        return True
    return False


def compute_recommendation_confidence(
    *,
    opportunity: Any,
    profile_strength: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> str:
    profile_level = str((profile_strength or {}).get("level") or "LOW").upper()
    semantic_score = float(evidence.get("semantic_score") or 0.0)
    strong_evidence = int(evidence.get("strong_evidence_count") or 0)
    exact_evidence = bool(
        evidence.get("skill_overlap")
        or evidence.get("role_match")
        or evidence.get("title_overlap")
        or evidence.get("industry_match")
    )

    if (
        profile_level in {"MEDIUM", "HIGH"}
        and strong_evidence >= 2
        and exact_evidence
        and semantic_score >= 0.55
    ):
        return CONFIDENCE_HIGH
    if exact_evidence or evidence.get("resume_signal") or semantic_score >= _thresholds(profile_strength).semantic_only:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def _set_quality_attr(item: Any, name: str, value: Any) -> None:
    if isinstance(item, dict):
        item[name] = value
    else:
        setattr(item, name, value)


def annotate_recommendation_quality(
    opportunity: Any,
    *,
    features: dict[str, Any] | None,
    profile_strength: dict[str, Any] | None,
) -> Any:
    evidence = build_recommendation_evidence(features, opportunity, profile_strength)
    confidence = compute_recommendation_confidence(
        opportunity=opportunity,
        profile_strength=profile_strength,
        evidence=evidence,
    )
    _set_quality_attr(opportunity, "recommendation_evidence", evidence)
    _set_quality_attr(opportunity, "recommendation_confidence", confidence)
    _set_quality_attr(opportunity, "recommendation_mode", recommendation_mode_for_profile(profile_strength))
    return opportunity


def filter_ranked_recommendations(
    ranked: list[Any],
    *,
    features: dict[str, Any] | None,
    profile_strength: dict[str, Any] | None,
    limit: int,
) -> list[Any]:
    accepted = []
    for opportunity in ranked:
        evidence = build_recommendation_evidence(features, opportunity, profile_strength)
        if not passes_recommendation_quality_gate(
            features=features,
            opportunity=opportunity,
            profile_strength=profile_strength,
            evidence=evidence,
        ):
            continue
        annotate_recommendation_quality(
            opportunity,
            features=features,
            profile_strength=profile_strength,
        )
        accepted.append(opportunity)
        if len(accepted) >= limit:
            break
    return accepted


def fallback_limit_for_profile(limit: int, profile_strength: dict[str, Any] | None) -> int:
    if recommendation_mode_for_profile(profile_strength) == "SPARSE_PROFILE":
        return max(1, min(int(limit or 1), 3))
    return int(limit or 1)


def sanitize_recommendation_reasons(reasons: list[str], evidence: dict[str, Any] | None) -> list[str]:
    evidence = evidence if isinstance(evidence, dict) else {}
    cleaned = []
    seen = set()
    for reason in reasons:
        label = str(reason or "").strip()
        if not label:
            continue
        key = normalize_lookup_key(label)
        if not key or key in seen:
            continue
        if key in GENERIC_REASON_LABELS:
            continue
        if key in GENERIC_SINGLE_WORD_REASONS:
            continue
        if key.startswith("location match") and any(normalize_lookup_key(item).startswith("location aligned") for item in cleaned):
            continue
        if key == "experience level aligned" and not evidence.get("strong_evidence_count"):
            continue
        seen.add(key)
        cleaned.append(label)
        if len(cleaned) >= MAX_QUALITY_REASONS:
            break
    return cleaned


def sanitize_recommendation_gaps(gaps: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for gap in gaps:
        label = str(gap or "").strip()
        if not label:
            continue
        key = normalize_lookup_key(label)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(label)
        if len(cleaned) >= MAX_QUALITY_GAPS:
            break
    return cleaned
