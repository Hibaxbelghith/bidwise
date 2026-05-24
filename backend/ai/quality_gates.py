from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from opportunities.normalization.text import normalize_lookup_key
from ai.business_families import (
    families_are_compatible,
    opportunity_llm_business_families,
    opportunity_text_business_families,
    profile_business_families,
)
from ai.hierarchy import (
    build_opportunity_hierarchy_signal,
    build_profile_hierarchy_signal,
    validate_hierarchy_match,
)
from .profile_strength import recommendation_mode_for_profile
from .recommendation_service import _clean_list, _get_value, _is_contextual_skill_match_allowed


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"

SEMANTIC_STRONG = "STRONG"
SEMANTIC_MEDIUM = "MEDIUM"
SEMANTIC_WEAK = "WEAK"

BUCKET_STRONG_MATCH = "STRONG_MATCH"
BUCKET_RELATED_REVIEW = "RELATED_REVIEW"

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
PREFERENCE_REASON_PREFIXES = (
    "location aligned",
    "location match",
)
PREFERENCE_REASON_LABELS = {
    "remote work preference aligned",
    "remote match",
    "hybrid work preference aligned",
    "hybrid match",
    "on site preference aligned",
    "on-site preference aligned",
    "on-site preference",
    "experience level aligned",
}
SENIORITY_CONFLICT_KEYWORDS = (
    "mid-senior",
    "mid senior",
    "lead",
    "senior",
    "sr",
    "confirme",
    "confirmed",
    "experimente",
    "experienced",
    "expert",
    "principal",
    "staff",
    "architect",
    "architecte",
    "head of",
)
RESPONSIBILITY_REVIEW_KEYWORDS = (
    "responsable",
    "manager",
    "directeur",
    "director",
    "head of",
)
GENERIC_ROLE_MATCH_TERMS = {
    "administration",
    "gestion de dossier",
    "gestion de dossiers",
    "it support",
    "network administration",
    "human resources",
    "ressources humaines",
    "accounting",
    "finance",
    "comptabilite",
    "comptabilité",
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
        if len(token) >= 3 or token in {"it", "ip"}
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


def _recommendation_debug(opportunity: Any) -> dict[str, Any]:
    debug = _get_value(opportunity, "recommendation_debug", {}) or {}
    return debug if isinstance(debug, dict) else {}


def _hierarchy_review_reason(features: dict[str, Any], opportunity: Any) -> str:
    debug = _recommendation_debug(opportunity)
    validation = debug.get("hierarchy_validation")
    if not isinstance(validation, dict):
        validation = validate_hierarchy_match(
            build_profile_hierarchy_signal(features),
            build_opportunity_hierarchy_signal(opportunity),
        ).as_debug()["hierarchy_validation"]

    issue = str(validation.get("hierarchy_issue") or "none")
    multiplier = float(validation.get("score_multiplier") or 1.0)
    if validation.get("needs_llm") and (
        int(validation.get("seniority_gap") or 0) >= 1
        or int(validation.get("responsibility_gap") or 0) >= 1
    ):
        title = normalize_lookup_key(_get_value(opportunity, "titre", ""))
        role_match, _matched_roles = _role_match(features, opportunity)
        _matched_skills, skill_count = _skill_overlap(features, opportunity)
        has_blocking_title = any(keyword in title for keyword in SENIORITY_CONFLICT_KEYWORDS) or any(
            keyword in title for keyword in RESPONSIBILITY_REVIEW_KEYWORDS
        )
        if role_match and skill_count >= 2 and _match_score(opportunity) >= 0.75 and not has_blocking_title:
            return ""
        return validation.get("reason") or "Hierarchy validation required before strong match"
    if issue in {"qualification_gap", "responsibility_gap"} or multiplier <= 0.72:
        return validation.get("reason") or "Hierarchy gap detected"
    if issue == "overqualified_scope":
        return validation.get("reason") or "Profile appears above the opportunity qualification scope"

    level = str((features or {}).get("experience_level") or "").strip().upper()
    if level not in {"DEBUTANT", "JUNIOR"}:
        return ""

    title = normalize_lookup_key(_get_value(opportunity, "titre", ""))
    if any(keyword in title for keyword in SENIORITY_CONFLICT_KEYWORDS):
        return "Seniority appears above the user's current level"

    debug = _recommendation_debug(opportunity)
    try:
        penalty = float(debug.get("experience_gap_penalty") or 0.0)
    except (TypeError, ValueError):
        penalty = 0.0
    if penalty >= 0.025:
        return "Seniority appears above the user's current level"
    return ""


def _has_sparse_opportunity_data(opportunity: Any) -> bool:
    if _clean_list(_get_value(opportunity, "skills", [])):
        return False
    description = str(_get_value(opportunity, "description", "") or "").strip()
    return len(description) < 300


def _semantic_strength(score: float, thresholds: QualityThresholds) -> str:
    if score >= thresholds.strong_semantic:
        return SEMANTIC_STRONG
    if score >= thresholds.medium_semantic:
        return SEMANTIC_MEDIUM
    return SEMANTIC_WEAK


def _skill_overlap_for_values(values: Any, opportunity: Any) -> tuple[list[str], int]:
    user_skills = _as_normalized_map(values)
    opportunity_skills = _as_normalized_map(_get_value(opportunity, "skills", []))
    title = normalize_lookup_key(_get_value(opportunity, "titre", ""))

    matched: list[str] = []
    seen = set()
    for key, label in user_skills.items():
        if not _is_contextual_skill_match_allowed(key, opportunity):
            continue
        if key in opportunity_skills or (key and key in title):
            if key not in seen:
                seen.add(key)
                matched.append(label)
    return matched, len(matched)


def _skill_overlap(features: dict[str, Any], opportunity: Any) -> tuple[list[str], int]:
    return _skill_overlap_for_values(features.get("skills"), opportunity)


def _role_match(features: dict[str, Any], opportunity: Any) -> tuple[bool, list[str]]:
    title = normalize_lookup_key(_get_value(opportunity, "titre", ""))
    if not title:
        return False, []
    title_tokens = _token_set(title)

    matched = []
    for role in _clean_list(features.get("target_roles")) or _clean_list(features.get("roles")):
        normalized_role = normalize_lookup_key(role)
        if normalized_role in GENERIC_ROLE_MATCH_TERMS:
            continue
        role_tokens = _token_set(normalized_role)
        if normalized_role and (
            normalized_role in title
            or (len(role_tokens) >= 2 and role_tokens.issubset(title_tokens))
        ):
            matched.append(str(role).strip())
    return bool(matched), matched[:2]


def _title_token_overlap(features: dict[str, Any], opportunity: Any) -> bool:
    title_tokens = _token_set(_get_value(opportunity, "titre", ""))
    if not title_tokens:
        return False
    profile_terms = []
    profile_terms.extend(_clean_list(features.get("target_roles")))
    profile_terms.extend(_clean_list(features.get("roles")))
    profile_terms.extend(_clean_list(features.get("profile_skills") or features.get("skills")))
    profile_tokens = set()
    for term in profile_terms:
        profile_tokens.update(_token_set(term))
    return len(profile_tokens.intersection(title_tokens)) >= 2


def _industry_match(features: dict[str, Any], opportunity: Any) -> bool:
    interests = set(_as_normalized_map(features.get("interests")).keys())
    industries = set(_as_normalized_map(_get_value(opportunity, "normalized_industries", [])).keys())
    return bool(interests and industries and interests.intersection(industries))


def _llm_family_match(features: dict[str, Any], opportunity: Any) -> tuple[bool, bool, list[str]]:
    profile_families = profile_business_families(features)
    llm_opportunity_families = opportunity_llm_business_families(opportunity)
    opportunity_families = llm_opportunity_families
    used_llm_families = bool(llm_opportunity_families)
    if not opportunity_families:
        opportunity_families = opportunity_text_business_families(
            opportunity,
            include_description=False,
        )
    if not profile_families or not opportunity_families:
        return False, False, []
    compatible = families_are_compatible(profile_families, opportunity_families)
    matched = sorted(profile_families.intersection(opportunity_families))
    return compatible, bool(not compatible), matched[:3]


def build_recommendation_evidence(
    features: dict[str, Any] | None,
    opportunity: Any,
    profile_strength: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = features if isinstance(features, dict) else {}
    thresholds = _thresholds(profile_strength)
    semantic_score = _semantic_score(opportunity)
    matched_skills, skill_overlap = _skill_overlap(features, opportunity)
    matched_profile_skills, profile_skill_overlap = _skill_overlap_for_values(
        features.get("profile_skills"),
        opportunity,
    )
    role_match, matched_roles = _role_match(features, opportunity)
    title_overlap = _title_token_overlap(features, opportunity)
    industry_match = _industry_match(features, opportunity)
    llm_family_match, llm_family_mismatch, matched_llm_families = _llm_family_match(features, opportunity)
    resume_present = bool(str(features.get("resume_text") or "").strip())
    resume_signal = resume_present and semantic_score >= thresholds.resume_semantic
    semantic_strength = _semantic_strength(semantic_score, thresholds)
    strong_semantic = semantic_score >= thresholds.semantic_only

    strong_evidence = 0
    strong_evidence += 1 if skill_overlap else 0
    strong_evidence += 1 if role_match or title_overlap else 0
    strong_evidence += 1 if industry_match and semantic_score >= thresholds.industry_semantic else 0
    strong_evidence += 1 if llm_family_match else 0
    strong_evidence += 1 if resume_signal else 0
    strong_evidence += 1 if strong_semantic else 0
    metier_signal_count = 0
    metier_signal_count += 1 if profile_skill_overlap else 0
    metier_signal_count += 1 if role_match or title_overlap else 0
    metier_signal_count += 1 if industry_match and semantic_score >= thresholds.industry_semantic else 0
    metier_signal_count += 1 if llm_family_match and not (role_match or title_overlap) else 0

    return {
        "skill_overlap": skill_overlap,
        "matched_skills": matched_skills,
        "profile_skill_overlap": profile_skill_overlap,
        "matched_profile_skills": matched_profile_skills,
        "role_match": role_match,
        "matched_roles": matched_roles,
        "title_overlap": title_overlap,
        "industry_match": industry_match,
        "llm_family_match": llm_family_match,
        "llm_family_mismatch": llm_family_mismatch,
        "matched_llm_families": matched_llm_families,
        "semantic_score": semantic_score,
        "semantic_strength": semantic_strength,
        "resume_signal": resume_signal,
        "resume_present": resume_present,
        "strong_semantic": strong_semantic,
        "strong_evidence_count": strong_evidence,
        "metier_signal_count": metier_signal_count,
    }


def evidence_summary(evidence: dict[str, Any] | None) -> dict[str, Any]:
    evidence = evidence if isinstance(evidence, dict) else {}
    return {
        "skill_overlap": int(evidence.get("skill_overlap") or 0),
        "profile_skill_overlap": int(evidence.get("profile_skill_overlap") or 0),
        "role_match": bool(evidence.get("role_match")),
        "title_overlap": bool(evidence.get("title_overlap")),
        "industry_match": bool(evidence.get("industry_match")),
        "llm_family_match": bool(evidence.get("llm_family_match")),
        "llm_family_mismatch": bool(evidence.get("llm_family_mismatch")),
        "matched_llm_families": list(evidence.get("matched_llm_families") or []),
        "semantic_strength": evidence.get("semantic_strength") or SEMANTIC_WEAK,
        "resume_signal": bool(evidence.get("resume_signal")),
    }


def has_meaningful_metier_evidence(evidence: dict[str, Any] | None) -> bool:
    evidence = evidence if isinstance(evidence, dict) else {}
    return bool(
        evidence.get("skill_overlap")
        or evidence.get("role_match")
        or evidence.get("title_overlap")
        or evidence.get("industry_match")
        or evidence.get("llm_family_match")
        or evidence.get("resume_signal")
        or evidence.get("strong_semantic")
    )


def _has_explicit_profile_metier_intent(features: dict[str, Any] | None) -> bool:
    features = features if isinstance(features, dict) else {}
    return bool(
        _clean_list(features.get("profile_skills"))
        or _clean_list(features.get("target_roles"))
        or features.get("normalized_profile_skills")
    )


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
        or evidence.get("llm_family_match")
    )
    if evidence.get("llm_family_mismatch") and not has_exact_evidence:
        return False

    if score < thresholds.min_score and not (
        has_exact_evidence and score >= thresholds.min_exact_evidence_score
    ):
        return False

    if evidence.get("skill_overlap"):
        if (
            _has_explicit_profile_metier_intent(features)
            and not evidence.get("profile_skill_overlap")
            and not (
                evidence.get("role_match")
                or evidence.get("title_overlap")
                or evidence.get("llm_family_match")
            )
        ):
            return False
        return True
    if evidence.get("role_match") or evidence.get("title_overlap"):
        return True
    if evidence.get("industry_match") and evidence.get("semantic_score", 0.0) >= thresholds.industry_semantic:
        return True
    if evidence.get("llm_family_match"):
        return True
    if evidence.get("resume_signal"):
        if _has_explicit_profile_metier_intent(features):
            return evidence.get("semantic_score", 0.0) >= max(0.72, thresholds.strong_semantic)
        return True
    if evidence.get("strong_semantic"):
        if _has_explicit_profile_metier_intent(features):
            return evidence.get("semantic_score", 0.0) >= max(0.72, thresholds.strong_semantic)
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
    metier_signals = int(evidence.get("metier_signal_count") or 0)
    profile_skill_overlap = int(evidence.get("profile_skill_overlap") or 0)
    exact_evidence = bool(
        profile_skill_overlap
        or evidence.get("role_match")
        or evidence.get("title_overlap")
        or evidence.get("industry_match")
        or evidence.get("llm_family_match")
    )

    if (
        profile_level in {"MEDIUM", "HIGH"}
        and strong_evidence >= 2
        and metier_signals >= 2
        and exact_evidence
        and semantic_score >= 0.55
    ):
        return CONFIDENCE_HIGH
    if exact_evidence or evidence.get("resume_signal") or semantic_score >= _thresholds(profile_strength).semantic_only:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def classify_recommendation_bucket(
    *,
    features: dict[str, Any] | None,
    opportunity: Any,
    evidence: dict[str, Any] | None = None,
) -> tuple[str, str]:
    features = features if isinstance(features, dict) else {}
    evidence = evidence or build_recommendation_evidence(features, opportunity)
    score = _match_score(opportunity)
    semantic_score = float(evidence.get("semantic_score") or 0.0)
    role_or_title = bool(evidence.get("role_match") or evidence.get("title_overlap"))
    skill_overlap = int(evidence.get("profile_skill_overlap") or evidence.get("skill_overlap") or 0)
    metier_signals = int(evidence.get("metier_signal_count") or 0)
    hierarchy_review_reason = _hierarchy_review_reason(features, opportunity)
    sparse_data = _has_sparse_opportunity_data(opportunity)

    if hierarchy_review_reason:
        return BUCKET_RELATED_REVIEW, hierarchy_review_reason

    if score >= 0.62 and role_or_title and (skill_overlap or semantic_score >= 0.60):
        if not skill_overlap:
            if sparse_data:
                return BUCKET_STRONG_MATCH, "Strong role and location match, but source has limited details"
            return BUCKET_STRONG_MATCH, "Strong role and semantic evidence"
        return BUCKET_STRONG_MATCH, "Strong role, skill, and semantic evidence"

    if score >= 0.68 and metier_signals >= 2 and semantic_score >= 0.60:
        return BUCKET_STRONG_MATCH, "Strong combined recommendation evidence"

    return BUCKET_RELATED_REVIEW, "Relevant but needs review before applying"


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
    bucket, bucket_reason = classify_recommendation_bucket(
        features=features,
        opportunity=opportunity,
        evidence=evidence,
    )
    _set_quality_attr(opportunity, "recommendation_bucket", bucket)
    _set_quality_attr(opportunity, "recommendation_bucket_reason", bucket_reason)
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


def _is_preference_reason(key: str) -> bool:
    if key in PREFERENCE_REASON_LABELS:
        return True
    if any(key.startswith(prefix) for prefix in PREFERENCE_REASON_PREFIXES):
        return True
    return key.endswith("contract aligned")


def sanitize_recommendation_reasons(reasons: list[str], evidence: dict[str, Any] | None) -> list[str]:
    evidence = evidence if isinstance(evidence, dict) else {}
    has_metier_evidence = has_meaningful_metier_evidence(evidence)
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
        if not has_metier_evidence and _is_preference_reason(key):
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
