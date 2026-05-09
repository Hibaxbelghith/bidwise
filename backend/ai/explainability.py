from django.conf import settings

from .recommendation_service import (
    EMPLOYMENT_KEYWORDS,
    EXPERIENCE_LEVEL_RANGES,
    HYBRID_KEYWORDS,
    REMOTE_KEYWORDS,
    _clean_list,
    _combined_opportunity_text,
    _get_value,
    _normalize_text,
    _ranges_overlap,
    _safe_int,
    _text_has_any,
)


MAX_REASONS = 5
MAX_GAPS = 3
MAX_SKILL_GAPS = 2
HIGH_SEMANTIC_THRESHOLD = 0.78
MEDIUM_SEMANTIC_THRESHOLD = 0.62
NOISY_SKILL_TOKENS = {
    "api",
    "apis",
    "it",
    "web",
    "office",
    "software",
    "development",
    "developer",
    "engineer",
    "sante",
    "santé",
    "qualite",
    "qualité",
    "hotellerie",
    "hôtellerie",
    "commercial",
    "mission",
    "poste",
    "machines",
}


def _append_unique(items, text, *, limit):
    label = str(text or "").strip()
    if not label or label in items or len(items) >= limit:
        return
    items.append(label)


def _normalized_map(values):
    mapped = {}
    for value in _clean_list(values):
        key = _normalize_text(value)
        if key and key not in mapped:
            mapped[key] = str(value).strip()
    return mapped


def _skill_reasons_and_gaps(features, opportunity):
    user_skills = _normalized_map(features.get("skills"))
    opportunity_skills = _normalized_map(_get_value(opportunity, "skills", []))
    if not opportunity_skills:
        return [], []

    matched = [
        opportunity_skills[key]
        for key in opportunity_skills
        if key in user_skills
    ]
    missing = [
        label
        for key, label in opportunity_skills.items()
        if key not in user_skills and key not in NOISY_SKILL_TOKENS
    ]

    reasons = []
    if matched:
        visible = matched[:2]
        _append_unique(
            reasons,
            f"Strong {' + '.join(visible)} alignment",
            limit=MAX_REASONS,
        )

    gaps = [
        f"Missing {skill} experience"
        for skill in missing[:MAX_SKILL_GAPS]
    ]
    return reasons, gaps


def _role_reason(features, opportunity):
    title = _normalize_text(_get_value(opportunity, "titre", ""))
    if not title:
        return ""
    for role in _clean_list(features.get("target_roles")) or _clean_list(features.get("roles")):
        normalized_role = _normalize_text(role)
        if normalized_role and normalized_role in title:
            return f"{role} role aligned"
    return ""


def _industry_reason(features, opportunity):
    user_interests = _normalized_map(features.get("interests"))
    opportunity_industries = _normalized_map(_get_value(opportunity, "normalized_industries", []))
    if not user_interests or not opportunity_industries:
        return ""

    for key, label in opportunity_industries.items():
        if key in user_interests:
            return f"{label.replace('_', ' ').title()} industry aligned"
    return ""


def _work_mode_reason_or_gap(features, opportunity):
    preferences = {
        _normalize_text(value)
        for value in _clean_list(features.get("work_modes")) or _clean_list(features.get("remote"))
    }
    if not preferences:
        return "", ""

    text = _combined_opportunity_text(opportunity)
    if "remote" in preferences:
        if _text_has_any(text, REMOTE_KEYWORDS):
            return "Remote work preference aligned", ""
        if _text_has_any(text, HYBRID_KEYWORDS):
            return "", "Remote preference differs"
    if "hybrid" in preferences:
        if _text_has_any(text, HYBRID_KEYWORDS):
            return "Hybrid work preference aligned", ""
        if _text_has_any(text, REMOTE_KEYWORDS):
            return "", "Hybrid preference differs"
    if preferences.intersection({"on site", "on-site", "on_site"}):
        if not (_text_has_any(text, REMOTE_KEYWORDS) or _text_has_any(text, HYBRID_KEYWORDS)):
            return "On-site preference aligned", ""
        return "", "Work mode preference differs"
    return "", ""


def _employment_reason_or_gap(features, opportunity):
    selected = {str(item or "").strip().upper() for item in _clean_list(features.get("employment_types"))}
    if not selected:
        return "", ""

    text = _combined_opportunity_text(opportunity)
    for employment_type in selected:
        keywords = EMPLOYMENT_KEYWORDS.get(employment_type, ())
        if keywords and _text_has_any(text, keywords):
            return f"{employment_type.replace('_', ' ').title()} contract aligned", ""

    return "", "Contract type may differ from your preference"


def _location_reason_or_gap(features, opportunity):
    profile_locations = _clean_list(features.get("locations"))
    if not profile_locations and features.get("location"):
        profile_locations = [features.get("location")]
    opportunity_location = _normalize_text(_get_value(opportunity, "ville", ""))
    if not profile_locations or not opportunity_location:
        return "", ""

    for profile_location in profile_locations:
        normalized_location = _normalize_text(profile_location)
        if (
            normalized_location
            and (
                normalized_location in opportunity_location
                or opportunity_location in normalized_location
            )
        ):
            return f"Location aligned: {_get_value(opportunity, 'ville', '')}", ""
    return "", "Location may differ from your preference"


def _experience_reason_or_gap(features, opportunity):
    level = str(features.get("experience_level") or "").strip().upper()
    profile_range = EXPERIENCE_LEVEL_RANGES.get(level)
    if not profile_range:
        return "", ""

    opp_min = _safe_int(_get_value(opportunity, "experience_min"))
    opp_max = _safe_int(_get_value(opportunity, "experience_max"))
    legacy_years = _safe_int(_get_value(opportunity, "experience_years"))
    if opp_min is None:
        opp_min = legacy_years
    if opp_max is None:
        opp_max = legacy_years
    if opp_min is None and opp_max is None:
        return "", ""

    if opp_min is None:
        opp_min = 0

    if _ranges_overlap(profile_range[0], profile_range[1], opp_min, opp_max):
        return "Experience level aligned", ""

    profile_max = profile_range[1]
    if profile_max is not None and opp_min > profile_max:
        return "", "Experience level below preferred range"
    if opp_max is not None and profile_range[0] > opp_max:
        return "", "Experience level above listed range"
    return "", "Experience range may differ"


def build_recommendation_explanation(features, opportunity):
    if not isinstance(features, dict):
        features = {}

    reasons = []
    gaps = []
    skill_reasons, skill_gaps = _skill_reasons_and_gaps(features, opportunity)
    for reason in skill_reasons:
        _append_unique(reasons, reason, limit=MAX_REASONS)

    for reason in (
        _role_reason(features, opportunity),
        _industry_reason(features, opportunity),
    ):
        _append_unique(reasons, reason, limit=MAX_REASONS)

    for resolver in (
        _work_mode_reason_or_gap,
        _employment_reason_or_gap,
        _location_reason_or_gap,
        _experience_reason_or_gap,
    ):
        reason, gap = resolver(features, opportunity)
        _append_unique(reasons, reason, limit=MAX_REASONS)
        _append_unique(gaps, gap, limit=MAX_GAPS)

    semantic_score = float(_get_value(opportunity, "semantic_score", 0.0) or 0.0)
    if semantic_score >= HIGH_SEMANTIC_THRESHOLD:
        _append_unique(reasons, "Strong semantic similarity with your profile", limit=MAX_REASONS)
    elif semantic_score >= MEDIUM_SEMANTIC_THRESHOLD:
        _append_unique(reasons, "Good semantic similarity with your profile", limit=MAX_REASONS)

    crossencoder_score = _safe_float(_get_value(opportunity, "crossencoder_score", 0.0))
    crossencoder_threshold = _safe_float(getattr(settings, "CROSS_ENCODER_REASON_THRESHOLD", 0.82))
    if crossencoder_score >= crossencoder_threshold:
        _append_unique(reasons, "High semantic alignment detected", limit=MAX_REASONS)
        if str(features.get("resume_text") or "").strip():
            _append_unique(reasons, "CV experience strongly matches this role", limit=MAX_REASONS)

    for gap in skill_gaps:
        _append_unique(gaps, gap, limit=MAX_GAPS)

    return {
        "reasons": reasons,
        "gaps": gaps,
    }


def _safe_float(value):
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0
