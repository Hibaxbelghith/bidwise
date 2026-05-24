import logging
import math
import re
import unicodedata
from datetime import date

from django.conf import settings

from ai.business_families import (
    families_are_compatible,
    opportunity_llm_business_families,
    opportunity_text_business_families,
    profile_business_families,
)
from ai.esco_recommendation_signals import build_esco_skill_overlap
from ai.esco_mapper import (
    role_families_for_text,
    role_families_for_values,
    skill_families_for_values,
)
from ai.jobbert import (
    build_jobbert_scores,
    build_precomputed_jobbert_scores,
    get_or_build_profile_jobbert_embedding,
    jobbert_adjustment,
    jobbert_enabled,
)
from ai.hierarchy import (
    build_opportunity_hierarchy_signal,
    build_profile_hierarchy_signal,
    validate_hierarchy_match,
)
from opportunities.normalization.employment import (
    CONTRACT_TYPE_CDI,
    CONTRACT_TYPE_INTERNSHIP,
    normalize_contract_types,
)
from opportunities.normalization.industries import normalize_industries


logger = logging.getLogger(__name__)


BUSINESS_BONUS_CAP = 0.25
FEEDBACK_BOOST = 0.05
DUPLICATE_COMPANY_PENALTY = 0.05
DUPLICATE_TITLE_PENALTY = 0.05
LOCATION_MATCH_BONUS = 0.10
LOCATION_MISMATCH_PENALTY = 0.08
STRICT_LOCATION_MATCH_BONUS = 0.06
REMOTE_MATCH_BONUS = 0.08
EMPLOYMENT_MATCH_BONUS = 0.05
EXPERIENCE_MATCH_BONUS = 0.05
ROLE_MATCH_BONUS = 0.06
ROLE_MATCH_FINAL_BOOST = 0.035
ROLE_AND_PROFILE_SKILL_DENSITY_BOOST = 0.03
ROLE_ONLY_EVIDENCE_PENALTY = 0.035
ISOLATED_SKILL_EVIDENCE_PENALTY = 0.035
GENERIC_SINGLE_SKILL_PENALTY = 0.08
SKILL_MATCH_BONUS = 0.025
SKILL_MATCH_BONUS_CAP = 0.10
NORMALIZED_SKILL_MATCH_BONUS = 0.01
NORMALIZED_SKILL_MATCH_BONUS_CAP = 0.03
ESCO_FAMILY_BONUS = 0.03
LLM_BUSINESS_FAMILY_BONUS = 0.04
LLM_BUSINESS_FAMILY_MISMATCH_PENALTY = 0.10
STRICT_BUSINESS_FAMILY_MISMATCH_PENALTY = 0.15
FAMILY_ONLY_SCORE_CAP = 0.58
SKILL_ONLY_EXPLICIT_ROLE_SCORE_CAP = 0.54
SPARSE_ROLE_ONLY_SCORE_CAP = 0.68
SECTOR_MATCH_BONUS = 0.025
SALARY_MATCH_BONUS = 0.02
SALARY_BELOW_EXPECTATION_PENALTY = 0.025
EXPERIENCE_GAP_PENALTY_SMALL = 0.02
EXPERIENCE_GAP_PENALTY_MEDIUM = 0.05
EXPERIENCE_GAP_PENALTY_LARGE = 0.08
EXPERIENCE_GAP_PENALTY_CAP = 0.10
NO_METIER_EVIDENCE_SEMANTIC_THRESHOLD = 0.60
NO_METIER_EVIDENCE_SCORE_MULTIPLIER = 0.50
CONTEXTUAL_GENERIC_SKILLS = {"support"}
GENERIC_SINGLE_SKILL_SIGNALS = {
    "excel",
    "support",
    "gestion",
    "management",
    "communication",
    "marketing",
    "vente",
    "sales",
    "javascript",
    "node",
    "node js",
    "python",
    "crm",
}
TECHNICAL_SUPPORT_CONTEXT_KEYWORDS = (
    "technical",
    "technician",
    "technicien",
    "technique",
    "engineer",
    "ingenieur",
    "ingénieur",
    "network",
    "reseau",
    "réseau",
    "server",
    "serveur",
    "system",
    "systeme",
    "système",
    "helpdesk",
    "infrastructure",
    "cisco",
    "bgp",
    "routing",
    "mpls",
)
SHORT_TECHNICAL_SUPPORT_CONTEXT_KEYWORDS = {"it", "ip"}
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
FAMILY_ROLE_TITLE_TERMS = {
    "administration": (
        "assistante administrative",
        "assistant administratif",
        "adjointe administrative",
        "adjoint administratif",
        "secretaire",
        "secrétaire",
        "gestionnaire administrative",
        "gestionnaire administratif",
        "employée administrative",
        "employe administratif",
    ),
    "it_network_support": (
        "technicien support",
        "support informatique",
        "helpdesk",
        "administrateur systemes",
        "administrateur systèmes",
        "systemes et reseaux",
        "systèmes et réseaux",
    ),
    "it_support_network": (
        "technicien support",
        "support informatique",
        "helpdesk",
        "administrateur systemes",
        "administrateur systèmes",
        "systemes et reseaux",
        "systèmes et réseaux",
    ),
    "accounting_finance_audit": (
        "assistant comptable",
        "assistante comptable",
        "comptable",
        "auditeur comptable",
        "auditrice comptable",
    ),
    "accounting_finance": (
        "assistant comptable",
        "assistante comptable",
        "comptable",
        "auditeur comptable",
        "auditrice comptable",
    ),
}

EXPERIENCE_LEVEL_RANGES = {
    "DEBUTANT": (0, 1),
    "JUNIOR": (1, 3),
    "CONFIRME": (3, 5),
    "SENIOR": (5, None),
}
EXPERIENCE_LEVEL_REPRESENTATIVE_YEARS = {
    "DEBUTANT": 0.5,
    "JUNIOR": 2.0,
    "CONFIRME": 4.0,
    "SENIOR": 6.0,
}
TITLE_SENIORITY_FLOORS = (
    ("staff", 6.0),
    ("principal", 6.0),
    ("architecte", 6.0),
    ("architect", 6.0),
    ("head of", 6.0),
    ("mid-senior", 4.0),
    ("mid senior", 4.0),
    ("lead engineer", 5.0),
    ("lead developer", 5.0),
    ("lead architect", 6.0),
    ("lead", 5.0),
    ("team lead", 5.0),
    ("tech lead", 5.0),
    ("senior", 4.0),
    ("sr", 4.0),
    ("expert", 4.0),
)

EMPLOYMENT_KEYWORDS = {
    "FULL_TIME": ("full time", "full-time", "temps plein", "cdi"),
    "PART_TIME": ("part time", "part-time", "temps partiel"),
    "CONTRACT": ("contract", "contractuel", "cdd"),
    "FREELANCE": ("freelance", "independent", "consultant"),
    "INTERNSHIP": ("internship", "intern", "stage", "stagiaire"),
}

REMOTE_KEYWORDS = ("remote", "teletravail", "a distance", "work from home")
HYBRID_KEYWORDS = ("hybrid", "hybride")
FULL_TIME_CONTRACT_TYPES = {CONTRACT_TYPE_CDI}
INTERNSHIP_CONTRACT_TYPES = {CONTRACT_TYPE_INTERNSHIP}


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


def _opportunity_llm_enrichment(opportunity):
    extra_data = _get_value(opportunity, "extra_data", {}) or {}
    if not isinstance(extra_data, dict):
        return {}
    enrichment = extra_data.get("llm_enrichment") or {}
    return enrichment if isinstance(enrichment, dict) else {}


def _llm_values(opportunity, *fields):
    enrichment = _opportunity_llm_enrichment(opportunity)
    values = []
    for field in fields:
        value = enrichment.get(field)
        if isinstance(value, list):
            values.extend(value)
        elif value:
            values.append(value)
    return _clean_list(values)


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


def _normalized_skill_bonus_enabled():
    return bool(getattr(settings, "RECOMMENDATION_ENABLE_NORMALIZED_SKILL_BONUS", True))


def _experience_gap_penalty_enabled():
    return bool(getattr(settings, "RECOMMENDATION_ENABLE_EXPERIENCE_GAP_PENALTY", True))


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


def _set_recommendation_debug(item, payload):
    debug_payload = payload if isinstance(payload, dict) else {}
    if isinstance(item, dict):
        item["recommendation_debug"] = debug_payload
        return item

    setattr(item, "recommendation_debug", debug_payload)
    return item


def _update_recommendation_debug(item, payload):
    extra_payload = payload if isinstance(payload, dict) else {}
    current_payload = _get_value(item, "recommendation_debug", {})
    merged = dict(current_payload if isinstance(current_payload, dict) else {})
    merged.update(extra_payload)
    return _set_recommendation_debug(item, merged)


def _append_reason(reasons, text):
    label = str(text or "").strip()
    if label and label not in reasons:
        reasons.append(label)


def _text_has_any(value, keywords):
    normalized = _normalize_text(value)
    return any(keyword in normalized for keyword in keywords)


def _work_mode_preferences(features):
    preferences = _clean_list(features.get("work_modes"))
    if not preferences and features.get("remote"):
        preferences = [features.get("remote")]
    return {
        _normalize_text(preference)
        for preference in preferences
        if _normalize_text(preference)
    }


def _combined_opportunity_text(opportunity):
    return " ".join(
        str(_get_value(opportunity, field, "") or "")
        for field in ("titre", "ville", "contract_type", "availability", "type_opportunite")
    )


def _employment_type_preferences(features):
    return {
        str(item or "").strip().upper()
        for item in _clean_list(features.get("employment_types"))
    }


def _opportunity_employment_type_signals(opportunity):
    normalized_contract_types = {
        str(item or "").strip().upper()
        for item in _clean_list(_get_value(opportunity, "normalized_contract_types", []))
    }
    normalized_contract_types.update(normalize_contract_types(_get_value(opportunity, "contract_type", "")))
    text = _combined_opportunity_text(opportunity)
    normalized_type = set(normalize_contract_types(_get_value(opportunity, "type_opportunite", "")))

    signals = set()
    if normalized_contract_types.intersection(INTERNSHIP_CONTRACT_TYPES):
        signals.add("INTERNSHIP")
    if normalized_contract_types.intersection(FULL_TIME_CONTRACT_TYPES):
        signals.add("FULL_TIME")
    if normalized_type.intersection(INTERNSHIP_CONTRACT_TYPES) or _text_has_any(text, EMPLOYMENT_KEYWORDS["INTERNSHIP"]):
        signals.add("INTERNSHIP")
    if _text_has_any(text, EMPLOYMENT_KEYWORDS["FULL_TIME"]):
        signals.add("FULL_TIME")
    return signals


def _employment_type_is_hard_incompatible(features, opportunity):
    selected = _employment_type_preferences(features)
    if selected == {"INTERNSHIP"}:
        opportunity_signals = _opportunity_employment_type_signals(opportunity)
        return opportunity_signals == {"FULL_TIME"}
    if selected == {"FULL_TIME"}:
        opportunity_signals = _opportunity_employment_type_signals(opportunity)
        return opportunity_signals == {"INTERNSHIP"}
    return False


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


def _strict_location_adjustment(features, opportunity, location_bonus):
    profile_locations = _clean_list(features.get("locations"))
    if not profile_locations and features.get("location"):
        profile_locations = [features.get("location")]
    if not profile_locations:
        return 0.0

    preferences = _work_mode_preferences(features)
    if preferences and not preferences.intersection({"on site", "on-site", "on_site", "hybrid"}):
        return 0.0

    opportunity_location = _normalize_text(_get_value(opportunity, "ville", ""))
    if not opportunity_location:
        return 0.0

    precise_locations = [
        _normalize_text(location)
        for location in profile_locations
        if len(_normalize_text(location)) >= 4
    ]
    if not precise_locations:
        return 0.0

    if location_bonus > 0:
        return STRICT_LOCATION_MATCH_BONUS
    return -LOCATION_MISMATCH_PENALTY


def _remote_bonus(features, opportunity, reasons):
    preferences = _work_mode_preferences(features)
    if not preferences:
        return 0.0

    text = _combined_opportunity_text(opportunity)
    if "remote" in preferences and _text_has_any(text, REMOTE_KEYWORDS):
        _append_reason(reasons, "Remote match")
        return REMOTE_MATCH_BONUS

    if "hybrid" in preferences and _text_has_any(text, HYBRID_KEYWORDS):
        _append_reason(reasons, "Hybrid match")
        return REMOTE_MATCH_BONUS

    if preferences.intersection({"on site", "on-site", "on_site"}) and not (
        _text_has_any(text, REMOTE_KEYWORDS) or _text_has_any(text, HYBRID_KEYWORDS)
    ):
        _append_reason(reasons, "On-site preference")
        return REMOTE_MATCH_BONUS / 2

    return 0.0


def _employment_bonus(features, opportunity, reasons):
    selected = _employment_type_preferences(features)
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


def _safe_float(value):
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _salary_expectation_range(features):
    salary_min = _safe_int((features or {}).get("salary_min"))
    salary_max = _safe_int((features or {}).get("salary_max"))
    salary = _safe_int((features or {}).get("salary"))

    if salary_min is None and salary is not None:
        salary_min = salary
    if salary_max is None and salary is not None:
        salary_max = salary
    if salary_min is None and salary_max is None:
        return None, None
    if salary_min is None:
        salary_min = salary_max
    if salary_max is None:
        salary_max = salary_min
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        salary_min, salary_max = salary_max, salary_min
    return salary_min, salary_max


def _opportunity_salary_range(opportunity):
    text = str(_get_value(opportunity, "salary", "") or "")
    if not text:
        return None, None

    numbers = []
    for raw in re.findall(r"\d[\d\s.,]*", text):
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            continue
        try:
            value = int(digits)
        except ValueError:
            continue
        if 100 <= value <= 100000:
            numbers.append(value)

    if not numbers:
        return None, None
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    low = min(numbers[:2])
    high = max(numbers[:2])
    return low, high


def _salary_bonus(features, opportunity, reasons):
    expected_min, expected_max = _salary_expectation_range(features)
    offer_min, offer_max = _opportunity_salary_range(opportunity)
    if expected_min is None or expected_max is None or offer_min is None or offer_max is None:
        return 0.0, {
            "salary_signal": "missing",
            "expected_min": expected_min,
            "expected_max": expected_max,
            "offer_min": offer_min,
            "offer_max": offer_max,
        }

    if offer_max < expected_min:
        return -SALARY_BELOW_EXPECTATION_PENALTY, {
            "salary_signal": "below_expectation",
            "expected_min": expected_min,
            "expected_max": expected_max,
            "offer_min": offer_min,
            "offer_max": offer_max,
        }

    if _ranges_overlap(expected_min, expected_max, offer_min, offer_max) or offer_min <= expected_max:
        _append_reason(reasons, "Salary range aligned")
        return SALARY_MATCH_BONUS, {
            "salary_signal": "aligned",
            "expected_min": expected_min,
            "expected_max": expected_max,
            "offer_min": offer_min,
            "offer_max": offer_max,
        }

    return 0.0, {
        "salary_signal": "above_expectation",
        "expected_min": expected_min,
        "expected_max": expected_max,
        "offer_min": offer_min,
        "offer_max": offer_max,
    }


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


def _profile_experience_years(features):
    explicit_years = _safe_float((features or {}).get("experience_years"))
    if explicit_years is not None:
        return explicit_years, "years"

    level = str((features or {}).get("experience_level") or "").strip().upper()
    representative_years = EXPERIENCE_LEVEL_REPRESENTATIVE_YEARS.get(level)
    if representative_years is not None:
        return representative_years, "level"

    if _employment_type_preferences(features or {}) == {"INTERNSHIP"}:
        return 0.0, "internship_preference"

    return None, ""


def _title_seniority_floor(opportunity):
    title = _normalize_text(_get_value(opportunity, "titre", ""))
    if not title:
        return 0.0, ""

    padded_title = f" {title} "
    for phrase, years in TITLE_SENIORITY_FLOORS:
        normalized_phrase = _normalize_text(phrase)
        if not normalized_phrase:
            continue
        token_phrase = f" {normalized_phrase} "
        if token_phrase in padded_title:
            return years, normalized_phrase
    return 0.0, ""


def _opportunity_experience_requirements(opportunity):
    opp_min = _safe_float(_get_value(opportunity, "experience_min"))
    opp_max = _safe_float(_get_value(opportunity, "experience_max"))
    legacy_years = _safe_float(_get_value(opportunity, "experience_years"))

    if opp_min is None and legacy_years is not None:
        opp_min = legacy_years
    if opp_max is None and legacy_years is not None:
        opp_max = legacy_years

    title_floor, title_keyword = _title_seniority_floor(opportunity)
    effective_min = opp_min if opp_min is not None else None
    if title_floor and (effective_min is None or title_floor > effective_min):
        effective_min = title_floor
    if opp_max is not None and effective_min is not None and opp_max < effective_min:
        opp_max = effective_min

    return {
        "min_years": opp_min,
        "max_years": opp_max,
        "legacy_years": legacy_years,
        "effective_min_years": effective_min,
        "title_floor_years": title_floor,
        "title_seniority_keyword": title_keyword,
    }


def _base_experience_gap_penalty(gap_years):
    if gap_years <= 0:
        return 0.0
    if gap_years <= 1.0:
        return EXPERIENCE_GAP_PENALTY_SMALL
    if gap_years <= 3.0:
        return EXPERIENCE_GAP_PENALTY_MEDIUM
    return EXPERIENCE_GAP_PENALTY_LARGE


def _experience_gap_penalty(features, opportunity, *, semantic_score=0.0, mode="complete"):
    requirements = _opportunity_experience_requirements(opportunity)
    profile_years, profile_source = _profile_experience_years(features)
    effective_min = requirements["effective_min_years"]

    debug_payload = {
        "experience_gap_detected": False,
        "experience_gap_penalty": 0.0,
        "parsed_experience_range": {
            "profile_years": profile_years,
            "profile_source": profile_source,
            "opportunity_min_years": requirements["min_years"],
            "opportunity_max_years": requirements["max_years"],
            "opportunity_legacy_years": requirements["legacy_years"],
            "effective_min_years": effective_min,
            "title_floor_years": requirements["title_floor_years"],
            "title_seniority_keyword": requirements["title_seniority_keyword"],
        },
        "fallback_override_if_any": "",
    }
    if not _experience_gap_penalty_enabled():
        return 0.0, debug_payload
    if profile_years is None or effective_min is None:
        return 0.0, debug_payload

    gap_years = max(0.0, float(effective_min) - float(profile_years))
    penalty = _base_experience_gap_penalty(gap_years)
    if penalty <= 0.0:
        return 0.0, debug_payload

    if (
        _employment_type_preferences(features or {}) == {"INTERNSHIP"}
        and requirements["title_floor_years"] >= 5.0
        and profile_years <= 1.0
    ):
        penalty += 0.02

    override_reasons = []
    if str(mode or "complete").strip().lower() == "partial":
        penalty *= 0.6
        override_reasons.append("partial_mode_scaled")
    if float(semantic_score or 0.0) >= 0.75:
        penalty *= 0.85
        override_reasons.append("strong_semantic_scaled")

    penalty = min(EXPERIENCE_GAP_PENALTY_CAP, round(float(penalty), 6))
    debug_payload["experience_gap_detected"] = penalty > 0.0
    debug_payload["experience_gap_penalty"] = penalty
    debug_payload["parsed_experience_range"]["gap_years"] = round(gap_years, 6)
    debug_payload["fallback_override_if_any"] = ",".join(override_reasons)
    return penalty, debug_payload


def _experience_gap_score_cap(experience_gap_debug):
    parsed = (experience_gap_debug or {}).get("parsed_experience_range") or {}
    gap_years = _safe_float(parsed.get("gap_years"))
    title_floor = _safe_float(parsed.get("title_floor_years"))
    if gap_years is None or gap_years <= 0:
        return None
    if gap_years >= 3.0 or (title_floor is not None and title_floor >= 5.0 and gap_years >= 2.0):
        return 0.58
    if gap_years >= 2.0:
        return 0.62
    if gap_years >= 1.0:
        return 0.68
    return None


def _role_matches(features, opportunity):
    role_texts = [
        _get_value(opportunity, "titre", ""),
        *_llm_values(opportunity, "canonical_role", "target_roles"),
    ]
    searchable = " ".join(_normalize_text(value) for value in role_texts if value).strip()
    if not searchable:
        return []
    searchable_tokens = {
        token
        for token in searchable.split()
        if len(token) >= 3 or token in SHORT_TECHNICAL_SUPPORT_CONTEXT_KEYWORDS
    }

    matches = []
    for role in _clean_list(features.get("roles")):
        normalized_role = _normalize_text(role)
        if normalized_role in GENERIC_ROLE_MATCH_TERMS:
            continue
        role_tokens = {
            token
            for token in normalized_role.split()
            if len(token) >= 3 or token in SHORT_TECHNICAL_SUPPORT_CONTEXT_KEYWORDS
        }
        if normalized_role and (
            normalized_role in searchable
            or (len(role_tokens) >= 2 and role_tokens.issubset(searchable_tokens))
        ):
            matches.append(role)
    if not matches:
        title = _normalize_text(_get_value(opportunity, "titre", ""))
        for family in sorted(profile_business_families(features or {})):
            for term in FAMILY_ROLE_TITLE_TERMS.get(family, ()):
                normalized_term = _normalize_text(term)
                if normalized_term and normalized_term in title:
                    matches.append(term)
                    return matches
    return matches


def _role_bonus(features, opportunity, reasons):
    matches = _role_matches(features, opportunity)
    if matches:
        _append_reason(reasons, matches[0])
        return ROLE_MATCH_BONUS
    return 0.0


def _skill_matches(features, opportunity):
    user_skills = _clean_list(features.get("skills"))
    if not user_skills:
        return []

    opportunity_skill_values = (
        _clean_list(_get_value(opportunity, "skills", []))
        + _llm_values(opportunity, "skills", "tools", "domains")
    )
    opportunity_skills = {
        _normalize_text(skill)
        for skill in opportunity_skill_values
    }
    title = _normalize_text(
        " ".join([
            str(_get_value(opportunity, "titre", "") or ""),
            " ".join(_llm_values(opportunity, "canonical_role", "target_roles")),
        ])
    )

    matches = []
    for skill in user_skills:
        normalized_skill = _normalize_text(skill)
        if not normalized_skill:
            continue
        if not _is_contextual_skill_match_allowed(normalized_skill, opportunity):
            continue
        if normalized_skill in opportunity_skills or normalized_skill in title:
            matches.append(skill)

    return matches


def _is_contextual_skill_match_allowed(normalized_skill, opportunity):
    if normalized_skill not in CONTEXTUAL_GENERIC_SKILLS:
        return True
    text = " ".join(
        str(_get_value(opportunity, field, "") or "")
        for field in ("titre", "description")
    )
    text = _normalize_text(text)
    if any(keyword in text for keyword in TECHNICAL_SUPPORT_CONTEXT_KEYWORDS):
        return True
    tokens = set(re.findall(r"[a-z0-9]+", text))
    return bool(tokens.intersection(SHORT_TECHNICAL_SUPPORT_CONTEXT_KEYWORDS))


def _sector_values_from_opportunity(opportunity):
    extra_data = _get_value(opportunity, "extra_data", {})
    if not isinstance(extra_data, dict):
        extra_data = {}
    return _clean_list(_get_value(opportunity, "normalized_industries", [])) + _clean_list(
        extra_data.get("company_sector")
    )


def _sector_match_bonus(features, opportunity, reasons):
    profile_sectors = _clean_list((features or {}).get("interests"))
    if not profile_sectors:
        return 0.0, []

    profile_keys = {
        _normalize_text(value)
        for value in profile_sectors
        if _normalize_text(value)
    }
    for canonical in normalize_industries(profile_sectors):
        key = _normalize_text(canonical)
        if key:
            profile_keys.add(key)

    opportunity_values = _sector_values_from_opportunity(opportunity)
    opportunity_keys = {
        _normalize_text(value)
        for value in opportunity_values
        if _normalize_text(value)
    }
    for canonical in normalize_industries(opportunity_values):
        key = _normalize_text(canonical)
        if key:
            opportunity_keys.add(key)

    matches = sorted(profile_keys.intersection(opportunity_keys))
    if not matches:
        return 0.0, []

    _append_reason(reasons, "Sector preference aligned")
    return SECTOR_MATCH_BONUS, matches[:3]


def _skill_bonus(features, opportunity, reasons):
    matches = _skill_matches(features, opportunity)
    for skill in matches[:3]:
        _append_reason(reasons, skill)

    return min(SKILL_MATCH_BONUS_CAP, len(matches) * SKILL_MATCH_BONUS), matches


def _normalized_skill_bonus(features, opportunity):
    overlap = build_esco_skill_overlap(
        (features or {}).get("normalized_skills"),
        _get_value(opportunity, "normalized_skills", []),
    )
    if not _normalized_skill_bonus_enabled():
        return 0.0, overlap

    if overlap.anchored_novel_overlap_count <= 0:
        return 0.0, overlap

    bonus = min(
        NORMALIZED_SKILL_MATCH_BONUS_CAP,
        overlap.anchored_novel_overlap_count * NORMALIZED_SKILL_MATCH_BONUS,
    )
    return bonus, overlap


def _profile_esco_families(features):
    families = set()
    families.update(role_families_for_values(_clean_list(features.get("target_roles"))))
    families.update(role_families_for_values(_clean_list(features.get("roles"))))
    families.update(skill_families_for_values(_clean_list(features.get("skills"))))
    return families


def _opportunity_esco_families(opportunity):
    families = set()
    families.update(role_families_for_text(_get_value(opportunity, "titre", "")))
    families.update(skill_families_for_values(_clean_list(_get_value(opportunity, "skills", []))))
    families.update(role_families_for_values(_llm_values(opportunity, "canonical_role", "target_roles")))
    families.update(skill_families_for_values(_llm_values(opportunity, "skills", "tools", "domains")))
    return families


def _esco_family_bonus(features, opportunity, semantic_score):
    if not isinstance(features, dict):
        return 0.0
    if _role_matches(features, opportunity) or _skill_matches(features, opportunity):
        return 0.0
    if semantic_score < NO_METIER_EVIDENCE_SEMANTIC_THRESHOLD:
        return 0.0

    profile_families = _profile_esco_families(features)
    if not profile_families:
        return 0.0

    opportunity_families = _opportunity_esco_families(opportunity)
    if not opportunity_families:
        return 0.0

    if profile_families.intersection(opportunity_families):
        return ESCO_FAMILY_BONUS
    return 0.0


def _llm_business_family_bonus(features, opportunity, reasons):
    profile_families = profile_business_families(features)
    opportunity_families = opportunity_llm_business_families(opportunity)
    if not profile_families or not opportunity_families:
        return 0.0
    if families_are_compatible(profile_families, opportunity_families):
        _append_reason(reasons, "Related job family signal detected")
        return LLM_BUSINESS_FAMILY_BONUS
    return 0.0


def _llm_business_family_mismatch_penalty(features, opportunity):
    profile_families = profile_business_families(features)
    opportunity_families = opportunity_llm_business_families(opportunity)
    if not profile_families or not opportunity_families:
        return 0.0
    if families_are_compatible(profile_families, opportunity_families):
        return 0.0
    profile_has_clear_intent = bool(
        _clean_list((features or {}).get("target_roles"))
        or _clean_list((features or {}).get("profile_skills"))
    )
    return (
        STRICT_BUSINESS_FAMILY_MISMATCH_PENALTY
        if profile_has_clear_intent
        else LLM_BUSINESS_FAMILY_MISMATCH_PENALTY
    )


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


def _business_score(features, opportunity, *, semantic_score=0.0):
    if not isinstance(features, dict):
        return 0.0, [], {}

    reasons = []
    location_bonus = _location_bonus(features, opportunity, reasons)
    remote_bonus = _remote_bonus(features, opportunity, reasons)
    raw_skill_bonus, raw_skill_matches = _skill_bonus(features, opportunity, reasons)
    normalized_skill_bonus, normalized_overlap = _normalized_skill_bonus(features, opportunity)
    employment_bonus = _employment_bonus(features, opportunity, reasons)
    experience_bonus = _experience_bonus(features, opportunity, reasons)
    role_bonus = _role_bonus(features, opportunity, reasons)
    esco_family_bonus = _esco_family_bonus(features, opportunity, semantic_score)
    llm_family_bonus = _llm_business_family_bonus(features, opportunity, reasons)
    sector_bonus, sector_matches = _sector_match_bonus(features, opportunity, reasons)
    salary_bonus, salary_debug = _salary_bonus(features, opportunity, reasons)
    has_metier_signal = bool(
        raw_skill_matches
        or normalized_overlap.shared_uris
        or role_bonus > 0
        or esco_family_bonus > 0
        or llm_family_bonus > 0
    )
    strict_location_adjustment = (
        _strict_location_adjustment(features, opportunity, location_bonus)
        if has_metier_signal
        else 0.0
    )

    total_bonus = (
        location_bonus
        + strict_location_adjustment
        + remote_bonus
        + raw_skill_bonus
        + normalized_skill_bonus
        + employment_bonus
        + experience_bonus
        + role_bonus
        + esco_family_bonus
        + llm_family_bonus
        + sector_bonus
        + salary_bonus
    )

    debug_payload = {
        "raw_skill_match_count": len(raw_skill_matches),
        "raw_skill_matches": raw_skill_matches[:3],
        "normalized_skill_overlap_count": len(normalized_overlap.shared_uris),
        "sector_match_count": len(sector_matches),
        "sector_matches": sector_matches,
        "salary": salary_debug,
        "normalized_skill_overlap_labels": list(normalized_overlap.shared_labels[:3]),
        "normalized_skill_overlap_uris": list(normalized_overlap.shared_uris[:3]),
        "normalized_skill_exact_overlap_count": normalized_overlap.exact_overlap_count,
        "normalized_skill_anchored_overlap_count": normalized_overlap.anchored_overlap_count,
        "normalized_skill_semantic_only_overlap_count": normalized_overlap.semantic_only_overlap_count,
        "normalized_skill_raw_equivalent_overlap_count": normalized_overlap.raw_equivalent_overlap_count,
        "normalized_skill_novel_overlap_count": normalized_overlap.anchored_novel_overlap_count,
        "normalized_skill_bonus": round(float(normalized_skill_bonus), 6),
        "business_components": {
            "location_bonus": round(float(location_bonus), 6),
            "strict_location_adjustment": round(float(strict_location_adjustment), 6),
            "remote_bonus": round(float(remote_bonus), 6),
            "raw_skill_bonus": round(float(raw_skill_bonus), 6),
            "normalized_skill_bonus": round(float(normalized_skill_bonus), 6),
            "employment_bonus": round(float(employment_bonus), 6),
            "experience_bonus": round(float(experience_bonus), 6),
            "role_bonus": round(float(role_bonus), 6),
            "esco_family_bonus": round(float(esco_family_bonus), 6),
            "llm_business_family_bonus": round(float(llm_family_bonus), 6),
            "sector_bonus": round(float(sector_bonus), 6),
            "salary_bonus": round(float(salary_bonus), 6),
        },
        "profile_business_families": sorted(profile_business_families(features)),
        "opportunity_llm_business_families": sorted(opportunity_llm_business_families(opportunity)),
    }
    if normalized_skill_bonus > 0:
        logger.debug(
            "Applied normalized ESCO skill bonus opportunity_id=%s bonus=%.4f overlap=%s raw_skill_matches=%s",
            _get_value(opportunity, "id", None),
            normalized_skill_bonus,
            list(normalized_overlap.shared_labels[:3]),
            raw_skill_matches[:3],
        )

    return min(BUSINESS_BONUS_CAP, total_bonus), reasons[:5], debug_payload


def _business_signal(business_score):
    if business_score <= 0:
        return 0.0
    return _clamp_score(business_score / BUSINESS_BONUS_CAP)


def _has_metier_evidence(features, opportunity, semantic_score):
    if semantic_score >= NO_METIER_EVIDENCE_SEMANTIC_THRESHOLD:
        return True
    return bool(
        _role_matches(features, opportunity)
        or _skill_matches(features, opportunity)
        or _has_compatible_business_family(features, opportunity)
    )


def _apply_no_metier_evidence_penalty(score, features, opportunity, semantic_score):
    if _has_metier_evidence(features, opportunity, semantic_score):
        return score
    return _clamp_score(score * NO_METIER_EVIDENCE_SCORE_MULTIPLIER)


def _apply_llm_business_family_mismatch_penalty(score, features, opportunity):
    penalty = _llm_business_family_mismatch_penalty(features or {}, opportunity)
    if penalty <= 0:
        return score, {"llm_business_family_mismatch_penalty": 0.0}
    return _clamp_score(score - penalty), {
        "llm_business_family_mismatch_penalty": round(float(penalty), 6)
    }


def _profile_skill_matches(features, opportunity):
    profile_skills = _clean_list((features or {}).get("profile_skills"))
    if not profile_skills:
        return []

    opportunity_skills = {
        _normalize_text(skill)
        for skill in _clean_list(_get_value(opportunity, "skills", []))
    }
    title = _normalize_text(_get_value(opportunity, "titre", ""))

    matches = []
    for skill in profile_skills:
        normalized_skill = _normalize_text(skill)
        if normalized_skill and (normalized_skill in opportunity_skills or normalized_skill in title):
            matches.append(skill)
    return matches


def _single_generic_skill_signal_penalty(features, opportunity):
    role_matches = _role_matches(features or {}, opportunity)
    if role_matches:
        return 0.0

    skill_matches = {
        _normalize_text(skill)
        for skill in _skill_matches(features or {}, opportunity)
        if _normalize_text(skill)
    }
    if len(skill_matches) != 1:
        return 0.0

    matched_skill = next(iter(skill_matches))
    if matched_skill not in GENERIC_SINGLE_SKILL_SIGNALS:
        return 0.0

    profile_families = profile_business_families(features or {})
    opportunity_families = opportunity_llm_business_families(opportunity)
    if opportunity_families and profile_families and families_are_compatible(profile_families, opportunity_families):
        return 0.0

    return GENERIC_SINGLE_SKILL_PENALTY


def _single_generic_skill_score_cap(features, opportunity):
    if _role_matches(features or {}, opportunity):
        return None

    skill_matches = {
        _normalize_text(skill)
        for skill in _skill_matches(features or {}, opportunity)
        if _normalize_text(skill)
    }
    if len(skill_matches) != 1:
        return None

    matched_skill = next(iter(skill_matches))
    if matched_skill not in GENERIC_SINGLE_SKILL_SIGNALS:
        return None

    profile_families = profile_business_families(features or {})
    opportunity_families = opportunity_llm_business_families(opportunity)
    if opportunity_families and profile_families and families_are_compatible(profile_families, opportunity_families):
        return None

    return 0.49


def _opportunity_business_families_for_scoring(opportunity):
    return opportunity_llm_business_families(opportunity) or opportunity_text_business_families(
        opportunity,
        include_description=False,
    )


def _has_compatible_business_family(features, opportunity):
    profile_families = profile_business_families(features or {})
    opportunity_families = _opportunity_business_families_for_scoring(opportunity)
    return bool(
        profile_families
        and opportunity_families
        and families_are_compatible(profile_families, opportunity_families)
    )


def _family_and_skill_evidence_boost(features, opportunity):
    return 0.0


def _family_only_score_cap(features, opportunity):
    if not _has_compatible_business_family(features, opportunity):
        return None
    if _role_matches(features or {}, opportunity):
        return None
    if _skill_matches(features or {}, opportunity) or _profile_skill_matches(features or {}, opportunity):
        return None
    return FAMILY_ONLY_SCORE_CAP


def _skill_only_explicit_role_score_cap(features, opportunity):
    features = features or {}
    if not _clean_list(features.get("target_roles")) and not _clean_list(features.get("roles")):
        return None
    if _role_matches(features, opportunity):
        return None
    if not _skill_matches(features, opportunity):
        return None

    profile_families = profile_business_families(features)
    opportunity_families = opportunity_llm_business_families(opportunity)
    if profile_families and opportunity_families and families_are_compatible(profile_families, opportunity_families):
        return None
    profile_esco_families = _profile_esco_families(features)
    opportunity_esco_families = _opportunity_esco_families(opportunity)
    if profile_esco_families and opportunity_esco_families and profile_esco_families.intersection(opportunity_esco_families):
        return None

    return SKILL_ONLY_EXPLICIT_ROLE_SCORE_CAP


def _sparse_role_only_score_cap(features, opportunity):
    if not _role_matches(features or {}, opportunity):
        return None
    if _skill_matches(features or {}, opportunity):
        return None
    if _llm_values(opportunity, "responsibilities", "requirements", "skills", "tools", "domains"):
        return None
    if _clean_list(_get_value(opportunity, "skills", [])):
        return None

    description = str(_get_value(opportunity, "description", "") or "").strip()
    if len(description) >= 220:
        return None
    return SPARSE_ROLE_ONLY_SCORE_CAP


def _metier_density_adjustment(features, opportunity, *, semantic_score=0.0):
    role_matches = _role_matches(features or {}, opportunity)
    profile_skill_matches = _profile_skill_matches(features or {}, opportunity)
    all_skill_matches = _skill_matches(features or {}, opportunity)
    opportunity_skills = _clean_list(_get_value(opportunity, "skills", []))
    explicit_profile_intent = bool(
        _clean_list((features or {}).get("profile_skills"))
        or _clean_list((features or {}).get("target_roles"))
    )

    if role_matches and not profile_skill_matches and not opportunity_skills:
        return -ROLE_ONLY_EVIDENCE_PENALTY

    if role_matches and profile_skill_matches:
        return ROLE_AND_PROFILE_SKILL_DENSITY_BOOST

    if (
        explicit_profile_intent
        and
        len(all_skill_matches) == 1
        and not role_matches
        and len(opportunity_skills) <= 1
        and float(semantic_score or 0.0) < 0.72
    ):
        normalized_match = _normalize_text(all_skill_matches[0])
        if normalized_match in GENERIC_SINGLE_SKILL_SIGNALS:
            return -GENERIC_SINGLE_SKILL_PENALTY
        return -ISOLATED_SKILL_EVIDENCE_PENALTY

    generic_skill_penalty = _single_generic_skill_signal_penalty(features or {}, opportunity)
    if generic_skill_penalty:
        return -generic_skill_penalty

    return 0.0


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


def _dedupe_ranked_opportunities(scored):
    seen = set()
    deduped = []
    for item in scored:
        key = (
            _duplicate_identity_title(_get_value(item, "titre", "")),
            _normalize_text(_get_value(item, "organisation_nom", "")),
            _normalize_text(_get_value(item, "ville", "")),
            str(_get_value(item, "type_opportunite", "") or "").strip().upper(),
        )
        if all(key) and key in seen:
            if isinstance(item, dict):
                item["duplicate_suppressed"] = True
            else:
                setattr(item, "duplicate_suppressed", True)
            continue
        if all(key):
            seen.add(key)
        deduped.append(item)
    return deduped


def _duplicate_identity_title(value):
    normalized = _normalize_text(value)
    if not normalized:
        return ""
    normalized = re.sub(r"\b(h f|f h|m f|f m|h/f|m/f|hf|mf)\b", " ", normalized)
    normalized = re.sub(r"\bjunior\b|\bsenior\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


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
    opportunity_list = list(opportunities)
    profile_hierarchy_signal = build_profile_hierarchy_signal(features or {})
    jobbert_scores = {}
    explicit_jobbert_profile_vector = _to_float_vector(
        (features or {}).get("_jobbert_profile_vector")
    )
    if jobbert_enabled() or explicit_jobbert_profile_vector:
        profile = (features or {}).get("_profile")
        profile_vector = explicit_jobbert_profile_vector
        if not profile_vector and profile is not None:
            profile_vector = get_or_build_profile_jobbert_embedding(profile, features or {})
        jobbert_scores = build_precomputed_jobbert_scores(profile_vector, opportunity_list)
        if not jobbert_scores and bool(getattr(settings, "JOBBERT_ALLOW_LIVE_FALLBACK", False)):
            jobbert_scores = build_jobbert_scores(features or {}, opportunity_list)
    for opportunity in opportunity_list:
        if _employment_type_is_hard_incompatible(features or {}, opportunity):
            continue

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
        jobbert_score = jobbert_scores.get(int(_get_value(opportunity, "id", 0) or 0), 0.0)
        ranking_semantic_score = max(float(semantic_score or 0.0), float(jobbert_score or 0.0))

        business_score, reasons, recommendation_debug = _business_score(
            features or {},
            opportunity,
            semantic_score=ranking_semantic_score,
        )
        feedback_score = _feedback_bonus(feedback or {}, opportunity, reasons)
        if mode == "partial":
            score = _clamp_score(
                (0.5 * ranking_semantic_score)
                + (0.3 * _business_signal(business_score))
                + (0.2 * _popularity_score(opportunity))
                + feedback_score
            )
        else:
            score = _clamp_score(
                (0.7 * ranking_semantic_score)
                + (0.3 * _business_signal(business_score))
                + feedback_score
            )
        experience_gap_penalty, experience_gap_debug = _experience_gap_penalty(
            features or {},
            opportunity,
            semantic_score=ranking_semantic_score,
            mode=mode,
        )
        score = _apply_no_metier_evidence_penalty(
            score,
            features or {},
            opportunity,
            ranking_semantic_score,
        )
        if _role_matches(features or {}, opportunity):
            score = _clamp_score(score + ROLE_MATCH_FINAL_BOOST)
        score = _clamp_score(
            score + _metier_density_adjustment(
                features or {},
                opportunity,
                semantic_score=semantic_score,
            )
        )
        score = _clamp_score(score + _family_and_skill_evidence_boost(features or {}, opportunity))
        score_cap = _single_generic_skill_score_cap(features or {}, opportunity)
        if score_cap is not None and score > score_cap:
            score = score_cap
        skill_only_role_cap = _skill_only_explicit_role_score_cap(features or {}, opportunity)
        if (
            jobbert_scores
            and not jobbert_score
            and not _role_matches(features or {}, opportunity)
            and not _skill_matches(features or {}, opportunity)
            and score > 0.45
        ):
            score = 0.45
        score, llm_family_penalty_debug = _apply_llm_business_family_mismatch_penalty(
            score,
            features or {},
            opportunity,
        )
        score = _clamp_score(score - experience_gap_penalty)
        opportunity_hierarchy_signal = build_opportunity_hierarchy_signal(opportunity)
        hierarchy_validation = validate_hierarchy_match(
            profile_hierarchy_signal,
            opportunity_hierarchy_signal,
        )
        apply_hierarchy_multiplier = not (
            mode == "partial"
            and not (_clean_list((features or {}).get("target_roles")) or _clean_list((features or {}).get("roles")))
        )
        has_explicit_profile_seniority = bool(
            str((features or {}).get("experience_level") or "").strip()
            or (features or {}).get("experience_years") is not None
        )
        if not has_explicit_profile_seniority and hierarchy_validation.hierarchy_issue == "seniority_gap":
            apply_hierarchy_multiplier = False
        if apply_hierarchy_multiplier and hierarchy_validation.score_multiplier < 1.0:
            score = _clamp_score(score * hierarchy_validation.score_multiplier)
        jobbert_delta = 0.0
        if jobbert_score:
            jobbert_delta = jobbert_adjustment(jobbert_score)
            if jobbert_delta > 0 and experience_gap_penalty >= EXPERIENCE_GAP_PENALTY_MEDIUM:
                jobbert_delta = min(jobbert_delta, 0.02)
            if jobbert_delta > 0 and hierarchy_validation.score_multiplier < 0.85:
                jobbert_delta = min(jobbert_delta, 0.015)
            score = _clamp_score(score + jobbert_delta)
            if jobbert_delta > 0:
                _append_reason(reasons, "Strong semantic job match")
        experience_score_cap = _experience_gap_score_cap(experience_gap_debug)
        if experience_score_cap is not None and score > experience_score_cap:
            score = experience_score_cap
        if skill_only_role_cap is not None and score > skill_only_role_cap:
            score = skill_only_role_cap
        sparse_role_cap = _sparse_role_only_score_cap(features or {}, opportunity)
        if sparse_role_cap is not None and score > sparse_role_cap:
            score = sparse_role_cap
        family_only_cap = _family_only_score_cap(features or {}, opportunity)
        if family_only_cap is not None and score > family_only_cap:
            score = family_only_cap
        if (
            hierarchy_validation.hierarchy_issue != "none"
            and hierarchy_validation.score_multiplier <= 0.72
            and apply_hierarchy_multiplier
            and score > 0.58
        ):
            score = 0.58
        if score < threshold:
            continue
        scored_item = _set_score(
            opportunity,
            score,
            semantic_score=ranking_semantic_score,
            business_score=business_score,
            feedback_score=feedback_score,
            reasons=reasons,
        )
        _set_recommendation_debug(scored_item, recommendation_debug)
        _update_recommendation_debug(scored_item, llm_family_penalty_debug)
        _update_recommendation_debug(scored_item, experience_gap_debug)
        _update_recommendation_debug(scored_item, hierarchy_validation.as_debug())
        _update_recommendation_debug(
            scored_item,
            {
                "base_semantic_score": round(float(semantic_score or 0.0), 4),
                "jobbert_score": round(float(jobbert_score or 0.0), 4),
                "jobbert_adjustment": round(float(jobbert_delta or 0.0), 6),
                "skill_only_explicit_role_score_cap": (
                    round(float(skill_only_role_cap), 6)
                    if skill_only_role_cap is not None
                    else 0.0
                ),
                "sparse_role_only_score_cap": (
                    round(float(sparse_role_cap), 6)
                    if sparse_role_cap is not None
                    else 0.0
                ),
            },
        )
        scored.append(scored_item)

    scored.sort(key=_sort_key, reverse=True)
    scored = _dedupe_ranked_opportunities(scored)
    scored = _apply_diversity_penalties(scored)
    if top_k is None:
        return scored

    try:
        limit = int(top_k)
    except (TypeError, ValueError):
        limit = len(scored)
    return scored[: max(0, limit)]
