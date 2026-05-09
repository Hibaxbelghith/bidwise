import math
import re
import unicodedata
from datetime import date


BUSINESS_BONUS_CAP = 0.25
FEEDBACK_BOOST = 0.05
DUPLICATE_COMPANY_PENALTY = 0.05
DUPLICATE_TITLE_PENALTY = 0.05
LOCATION_MATCH_BONUS = 0.10
REMOTE_MATCH_BONUS = 0.08
EMPLOYMENT_MATCH_BONUS = 0.05
EXPERIENCE_MATCH_BONUS = 0.05
ROLE_MATCH_BONUS = 0.06
SKILL_MATCH_BONUS = 0.025
SKILL_MATCH_BONUS_CAP = 0.10

EXPERIENCE_LEVEL_RANGES = {
    "DEBUTANT": (0, 1),
    "JUNIOR": (1, 3),
    "CONFIRME": (3, 5),
    "SENIOR": (5, None),
}

EMPLOYMENT_KEYWORDS = {
    "FULL_TIME": ("full time", "full-time", "temps plein", "cdi"),
    "PART_TIME": ("part time", "part-time", "temps partiel"),
    "CONTRACT": ("contract", "contractuel", "cdd"),
    "FREELANCE": ("freelance", "independent", "consultant"),
    "INTERNSHIP": ("internship", "intern", "stage", "stagiaire"),
}

REMOTE_KEYWORDS = ("remote", "teletravail", "a distance", "work from home")
HYBRID_KEYWORDS = ("hybrid", "hybride")


def get_score_label(score, *, is_fallback=False):
    if is_fallback:
        return "Recent"

    value = _clamp_score(score or 0.0)
    if value >= 0.85:
        return "Top match"
    if value >= 0.65:
        return "Good match"
    return "Worth a look"


def get_score_level(score, *, is_fallback=False):
    if is_fallback:
        return "TRENDING"

    value = _clamp_score(score or 0.0)
    if value >= 0.75:
        return "HIGH"
    if value >= 0.45:
        return "MEDIUM"
    return "LOW"


def _to_float_vector(vector):
    if not isinstance(vector, list) or not vector:
        return []

    values = []
    for item in vector:
        try:
            value = float(item)
        except (TypeError, ValueError):
            return []
        if not math.isfinite(value):
            return []
        values.append(value)
    return values


def _cosine_similarity(vector_a, vector_b):
    left = _to_float_vector(vector_a)
    right = _to_float_vector(vector_b)
    if not left or not right or len(left) != len(right):
        return None

    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    if norm_left == 0.0 or norm_right == 0.0:
        return None

    score = sum(a * b for a, b in zip(left, right)) / (norm_left * norm_right)
    return max(0.0, min(1.0, float(score)))


def _get_value(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _set_score(item, score, *, semantic_score, business_score, feedback_score, reasons):
    label = get_score_label(score)
    level = get_score_level(score)
    if isinstance(item, dict):
        ranked = item.copy()
        ranked["match_score"] = score
        ranked["score"] = score
        ranked["similarity_score"] = score
        ranked["semantic_score"] = semantic_score
        ranked["business_score"] = business_score
        ranked["feedback_score"] = feedback_score
        ranked["score_label"] = label
        ranked["score_level"] = level
        ranked["reason"] = reasons
        return ranked

    setattr(item, "match_score", score)
    setattr(item, "score", score)
    setattr(item, "similarity_score", score)
    setattr(item, "semantic_score", semantic_score)
    setattr(item, "business_score", business_score)
    setattr(item, "feedback_score", feedback_score)
    setattr(item, "score_label", label)
    setattr(item, "score_level", level)
    setattr(item, "reason", reasons)
    return item


def _update_score(item, score):
    label = get_score_label(score)
    level = get_score_level(score)
    if isinstance(item, dict):
        item["match_score"] = score
        item["score"] = score
        item["similarity_score"] = score
        item["score_label"] = label
        item["score_level"] = level
        return item

    setattr(item, "match_score", score)
    setattr(item, "score", score)
    setattr(item, "similarity_score", score)
    setattr(item, "score_label", label)
    setattr(item, "score_level", level)
    return item


def _clamp_score(value):
    return max(0.0, min(1.0, float(value)))


def _normalize_text(value):
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9\s+-]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _clean_list(value):
    if isinstance(value, list):
        raw_items = value
    elif value:
        raw_items = [value]
    else:
        raw_items = []

    cleaned = []
    for item in raw_items:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def _append_reason(reasons, text):
    label = str(text or "").strip()
    if label and label not in reasons:
        reasons.append(label)


def _text_has_any(value, keywords):
    normalized = _normalize_text(value)
    return any(keyword in normalized for keyword in keywords)


def _combined_opportunity_text(opportunity):
    return " ".join(
        str(_get_value(opportunity, field, "") or "")
        for field in ("titre", "ville", "contract_type", "availability", "type_opportunite")
    )


def _location_bonus(features, opportunity, reasons):
    profile_locations = _clean_list(features.get("locations"))
    if not profile_locations and features.get("location"):
        profile_locations = [features.get("location")]

    opportunity_location = _normalize_text(_get_value(opportunity, "ville", ""))
    if not profile_locations or not opportunity_location:
        return 0.0

    for profile_location in profile_locations:
        normalized_profile_location = _normalize_text(profile_location)
        if not normalized_profile_location:
            continue
        if (
            normalized_profile_location in opportunity_location
            or opportunity_location in normalized_profile_location
        ):
            _append_reason(reasons, f"Location match: {_get_value(opportunity, 'ville', '')}")
            return LOCATION_MATCH_BONUS
    return 0.0


def _remote_bonus(features, opportunity, reasons):
    preference = _normalize_text(features.get("remote"))
    if not preference:
        return 0.0

    text = _combined_opportunity_text(opportunity)
    if preference == "remote" and _text_has_any(text, REMOTE_KEYWORDS):
        _append_reason(reasons, "Remote match")
        return REMOTE_MATCH_BONUS

    if preference == "hybrid" and _text_has_any(text, HYBRID_KEYWORDS):
        _append_reason(reasons, "Hybrid match")
        return REMOTE_MATCH_BONUS

    if preference in {"on site", "on-site", "on_site"} and not (
        _text_has_any(text, REMOTE_KEYWORDS) or _text_has_any(text, HYBRID_KEYWORDS)
    ):
        _append_reason(reasons, "On-site preference")
        return REMOTE_MATCH_BONUS / 2

    return 0.0


def _employment_bonus(features, opportunity, reasons):
    selected = {str(item or "").strip().upper() for item in _clean_list(features.get("employment_types"))}
    if not selected:
        return 0.0

    text = _combined_opportunity_text(opportunity)
    for employment_type in selected:
        keywords = EMPLOYMENT_KEYWORDS.get(employment_type, ())
        if keywords and _text_has_any(text, keywords):
            _append_reason(reasons, employment_type.replace("_", " ").title())
            return EMPLOYMENT_MATCH_BONUS
    return 0.0


def _ranges_overlap(left_min, left_max, right_min, right_max):
    if left_max is None:
        left_max = float("inf")
    if right_max is None:
        right_max = float("inf")
    return left_min <= right_max and right_min <= left_max


def _safe_int(value):
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _experience_bonus(features, opportunity, reasons):
    level = str(features.get("experience_level") or "").strip().upper()
    profile_range = EXPERIENCE_LEVEL_RANGES.get(level)
    if not profile_range:
        return 0.0

    opp_min = _safe_int(_get_value(opportunity, "experience_min"))
    opp_max = _safe_int(_get_value(opportunity, "experience_max"))
    legacy_years = _safe_int(_get_value(opportunity, "experience_years"))

    if opp_min is None:
        opp_min = legacy_years
    if opp_max is None:
        opp_max = legacy_years
    if opp_min is None and opp_max is None:
        return 0.0

    if opp_min is None:
        opp_min = 0
    if _ranges_overlap(profile_range[0], profile_range[1], opp_min, opp_max):
        _append_reason(reasons, "Experience match")
        return EXPERIENCE_MATCH_BONUS
    return 0.0


def _role_bonus(features, opportunity, reasons):
    title = _normalize_text(_get_value(opportunity, "titre", ""))
    if not title:
        return 0.0

    for role in _clean_list(features.get("roles")):
        normalized_role = _normalize_text(role)
        if normalized_role and normalized_role in title:
            _append_reason(reasons, role)
            return ROLE_MATCH_BONUS
    return 0.0


def _skill_bonus(features, opportunity, reasons):
    user_skills = _clean_list(features.get("skills"))
    if not user_skills:
        return 0.0

    opportunity_skills = {
        _normalize_text(skill)
        for skill in _clean_list(_get_value(opportunity, "skills", []))
    }
    title = _normalize_text(_get_value(opportunity, "titre", ""))

    matches = []
    for skill in user_skills:
        normalized_skill = _normalize_text(skill)
        if not normalized_skill:
            continue
        if normalized_skill in opportunity_skills or normalized_skill in title:
            matches.append(skill)

    for skill in matches[:3]:
        _append_reason(reasons, skill)

    return min(SKILL_MATCH_BONUS_CAP, len(matches) * SKILL_MATCH_BONUS)


def _feedback_bonus(feedback, opportunity, reasons):
    if not isinstance(feedback, dict):
        return 0.0

    opportunity_vector = _to_float_vector(_get_value(opportunity, "embedding_vector"))
    for applied_vector in feedback.get("applied_embeddings", []):
        similarity = _cosine_similarity(opportunity_vector, applied_vector)
        if similarity is not None and similarity >= 0.65:
            _append_reason(reasons, "Similar to your applications")
            return FEEDBACK_BOOST

    applied_skills = {
        _normalize_text(skill)
        for skill in _clean_list(feedback.get("applied_skills", []))
    }
    opportunity_skills = {
        _normalize_text(skill)
        for skill in _clean_list(_get_value(opportunity, "skills", []))
    }
    if applied_skills and opportunity_skills and applied_skills.intersection(opportunity_skills):
        _append_reason(reasons, "Similar to your applications")
        return FEEDBACK_BOOST

    return 0.0


def _business_score(features, opportunity):
    if not isinstance(features, dict):
        return 0.0, []

    reasons = []
    bonus = 0.0
    bonus += _location_bonus(features, opportunity, reasons)
    bonus += _remote_bonus(features, opportunity, reasons)
    bonus += _skill_bonus(features, opportunity, reasons)
    bonus += _employment_bonus(features, opportunity, reasons)
    bonus += _experience_bonus(features, opportunity, reasons)
    bonus += _role_bonus(features, opportunity, reasons)

    return min(BUSINESS_BONUS_CAP, bonus), reasons[:5]


def _business_signal(business_score):
    if business_score <= 0:
        return 0.0
    return _clamp_score(business_score / BUSINESS_BONUS_CAP)


def _popularity_score(opportunity):
    application_count = _safe_int(_get_value(opportunity, "application_count"))
    if application_count:
        return min(1.0, application_count / 10.0)

    publication_date = _get_value(opportunity, "date_publication")
    if hasattr(publication_date, "toordinal"):
        age_days = max(0, (date.today() - publication_date).days)
        if age_days <= 7:
            return 0.8
        if age_days <= 30:
            return 0.5
        if age_days <= 90:
            return 0.25
    return 0.1


def _title_cluster(value):
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    stop_words = {"senior", "junior", "remote", "hybrid", "full", "time", "stage"}
    tokens = [token for token in normalized.split() if token not in stop_words]
    return " ".join(tokens[:4])


def _apply_diversity_penalties(scored):
    company_counts = {}
    title_counts = {}
    diversified = []

    for item in scored:
        company = _normalize_text(_get_value(item, "organisation_nom", ""))
        title = _title_cluster(_get_value(item, "titre", ""))
        penalty = 0.0

        if company:
            penalty += company_counts.get(company, 0) * DUPLICATE_COMPANY_PENALTY
            company_counts[company] = company_counts.get(company, 0) + 1

        if title:
            penalty += title_counts.get(title, 0) * DUPLICATE_TITLE_PENALTY
            title_counts[title] = title_counts.get(title, 0) + 1

        if penalty:
            adjusted_score = _clamp_score(float(_get_value(item, "match_score", 0.0) or 0.0) - penalty)
            if isinstance(item, dict):
                item["diversity_penalty"] = penalty
            else:
                setattr(item, "diversity_penalty", penalty)
            _update_score(item, adjusted_score)

        diversified.append(item)

    diversified.sort(key=_sort_key, reverse=True)
    return diversified


def _sort_key(item):
    publication_date = _get_value(item, "date_publication")
    date_key = publication_date.toordinal() if hasattr(publication_date, "toordinal") else 0
    return (
        float(_get_value(item, "match_score", 0.0) or 0.0),
        date_key,
        int(_get_value(item, "id", 0) or 0),
    )


def rank_opportunities(
    user_embedding,
    opportunities,
    features=None,
    feedback=None,
    mode="complete",
    top_k=None,
    min_score=0.0,
):
    """
    Return opportunities ranked by semantic similarity plus business rules.

    The returned objects are the original model instances with match_score and
    similarity_score attributes attached. Dict inputs are copied before scores
    are added so callers do not get accidental mutation.
    """
    source_vector = _to_float_vector(user_embedding)
    mode = str(mode or "complete").strip().lower()
    if not source_vector and mode != "partial":
        return []

    try:
        threshold = float(min_score or 0.0)
    except (TypeError, ValueError):
        threshold = 0.0

    scored = []
    for opportunity in opportunities:
        semantic_score = 0.0
        if source_vector:
            semantic_score = _cosine_similarity(
                source_vector,
                _get_value(opportunity, "embedding_vector"),
            )
        if semantic_score is None:
            if mode != "partial":
                continue
            semantic_score = 0.0

        business_score, reasons = _business_score(features or {}, opportunity)
        feedback_score = _feedback_bonus(feedback or {}, opportunity, reasons)
        if mode == "partial":
            score = _clamp_score(
                (0.5 * semantic_score)
                + (0.3 * _business_signal(business_score))
                + (0.2 * _popularity_score(opportunity))
                + feedback_score
            )
        else:
            score = _clamp_score(
                (0.7 * semantic_score)
                + (0.3 * _business_signal(business_score))
                + feedback_score
            )
        if score < threshold:
            continue
        scored.append(
            _set_score(
                opportunity,
                score,
                semantic_score=semantic_score,
                business_score=business_score,
                feedback_score=feedback_score,
                reasons=reasons,
            )
        )

    scored.sort(key=_sort_key, reverse=True)
    scored = _apply_diversity_penalties(scored)
    if top_k is None:
        return scored

    try:
        limit = int(top_k)
    except (TypeError, ValueError):
        limit = len(scored)
    return scored[: max(0, limit)]
