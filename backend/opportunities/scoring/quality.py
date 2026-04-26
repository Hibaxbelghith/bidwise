import re
import unicodedata
from datetime import datetime
from typing import Any

from opportunities.scraping.scraper_utils import (
    classify_source_item_url,
    normalize_organization_name,
)


DATE_CONFIDENCE_EXACT = "EXACT"
DATE_CONFIDENCE_ESTIMATED = "ESTIMATED"
DATE_CONFIDENCE_FALLBACK = "FALLBACK"
MISSING_SIGNAL_SCORE = 0.15

SOURCE_RELIABILITY = {
    "Keejob": 1.0,
    "EmploiTunisie": 0.95,
    "LinkedIn": 0.9,
    "MarchesPublics": 0.98,
}

JOB_SIGNAL_WEIGHTS = {
    "organization": 0.16,
    "description": 0.2,
    "location": 0.08,
    "url": 0.08,
    "date": 0.08,
    "skills": 0.12,
    "title": 0.08,
    "completeness": 0.05,
    "skill_alignment": 0.07,
    "freshness": 0.05,
    "consistency": 0.03,
}

PROJECT_SIGNAL_WEIGHTS = {
    "organization": 0.2,
    "description": 0.22,
    "location": 0.1,
    "url": 0.1,
    "date": 0.12,
    "title": 0.1,
    "completeness": 0.08,
    "extra_data": 0.08,
    "freshness": 0.05,
}

GENERIC_TITLE_WORDS = {
    "job",
    "jobs",
    "emploi",
    "offre",
    "offres",
    "poste",
    "tunisia",
    "tunisie",
    "france",
    "remote",
    "urgent",
    "opportunity",
    "opportunite",
    "project",
    "projet",
    "mission",
}

PROJECT_TYPE_MARKERS = {"project", "projet"}


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _normalize_text(value: Any) -> str:
    text = _as_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            text = _as_text(item)
            if text:
                result.append(text)
        return result
    text = _as_text(value)
    return [text] if text else []


def normalize_date_confidence(value: Any) -> str:
    normalized = _normalize_text(value).upper()
    if normalized == DATE_CONFIDENCE_EXACT:
        return DATE_CONFIDENCE_EXACT
    if normalized == DATE_CONFIDENCE_ESTIMATED:
        return DATE_CONFIDENCE_ESTIMATED
    return DATE_CONFIDENCE_FALLBACK


def infer_date_confidence(value: Any) -> str:
    text = _as_text(value)
    if not text:
        return DATE_CONFIDENCE_FALLBACK
    normalized = _normalize_text(text)
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", text) or re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", text):
        return DATE_CONFIDENCE_EXACT
    if any(token in normalized for token in ("today", "aujourd", "yesterday", "hier", "day", "jours", "semaine", "week")):
        return DATE_CONFIDENCE_ESTIMATED
    return DATE_CONFIDENCE_FALLBACK


def _score_signal(score: float, available: bool = True, reason: str = "") -> dict[str, Any]:
    return {
        "score": max(0.0, min(float(score or 0.0), 1.0)),
        "available": bool(available),
        "reason": reason,
    }


def _score_organization(org: Any) -> dict[str, Any]:
    text = _as_text(org)
    if not text:
        return _score_signal(0.0, False, "missing")

    normalized = normalize_organization_name(text)
    if not normalized:
        return _score_signal(0.4, True, "weak")
    if len(normalized) < 3:
        return _score_signal(0.6, True, "short")
    return _score_signal(1.0, True, "good")


def _score_description(description: Any) -> dict[str, Any]:
    text = _as_text(description)
    if not text:
        return _score_signal(0.0, False, "missing")

    length = len(text)
    structure_bonus = 0.0
    if "\n" in text:
        structure_bonus += 0.08
    if re.search(r"[:\-]\s", text):
        structure_bonus += 0.07
    if re.search(r"[.;]\s", text):
        structure_bonus += 0.05

    if length >= 900:
        base = 0.92
        reason = "rich"
    elif length >= 500:
        base = 0.8
        reason = "good"
    elif length >= 220:
        base = 0.62
        reason = "medium"
    elif length >= 80:
        base = 0.42
        reason = "short"
    else:
        base = 0.22
        reason = "thin"

    return _score_signal(min(base + structure_bonus, 1.0), True, reason)


def _score_location(location: Any) -> dict[str, Any]:
    text = _as_text(location)
    if not text:
        return _score_signal(0.0, False, "missing")
    if len(text.split()) >= 2:
        return _score_signal(1.0, True, "specific")
    return _score_signal(0.7, True, "basic")


def _score_url(url: Any) -> dict[str, Any]:
    text = _as_text(url)
    if not text:
        return _score_signal(0.0, False, "missing")

    url_type = classify_source_item_url(text)
    if url_type == "detail_like":
        return _score_signal(1.0, True, "detail")
    if url_type == "generic_listing":
        return _score_signal(0.4, True, "listing")
    return _score_signal(0.2, True, "weak")


def _score_date_confidence(confidence: Any) -> dict[str, Any]:
    value = _as_text(confidence).upper()
    if not value:
        return _score_signal(0.0, False, "missing")
    if value == DATE_CONFIDENCE_EXACT:
        return _score_signal(1.0, True, "exact")
    if value == DATE_CONFIDENCE_ESTIMATED:
        return _score_signal(0.75, True, "estimated")
    return _score_signal(0.5, True, "fallback")


def _score_skills(skills: Any) -> dict[str, Any]:
    items = _clean_list(skills)
    if not items:
        return _score_signal(0.0, False, "missing")

    normalized_items = [_normalize_text(item) for item in items if _normalize_text(item)]
    unique_count = len(set(normalized_items))
    diversity_ratio = unique_count / max(len(normalized_items), 1)

    if unique_count >= 6:
        base = 0.95
    elif unique_count >= 4:
        base = 0.8
    elif unique_count >= 2:
        base = 0.62
    else:
        base = 0.4

    score = min(base * (0.85 + 0.15 * diversity_ratio), 1.0)
    return _score_signal(score, True, "diverse" if diversity_ratio > 0.8 else "limited")


def _score_title(title: Any) -> dict[str, Any]:
    text = _as_text(title)
    if not text:
        return _score_signal(0.0, False, "missing")

    words = _normalize_text(text).split()
    if not words:
        return _score_signal(0.0, False, "missing")

    filtered_words = [word for word in words if word not in GENERIC_TITLE_WORDS]
    has_role_signal = len(filtered_words) >= 2
    all_generic = not filtered_words

    if len(words) <= 1:
        return _score_signal(0.2, True, "too_short")
    if all_generic:
        return _score_signal(0.15, True, "generic")
    if len(filtered_words) == 1 and any(word in {"tunis", "sfax", "sousse", "ariana", "ben", "arous"} for word in filtered_words):
        return _score_signal(0.2, True, "location_like")
    if not has_role_signal:
        return _score_signal(0.45, True, "weak")
    if len(words) >= 3:
        return _score_signal(0.9, True, "specific")
    return _score_signal(0.7, True, "good")


def _score_completeness(**fields: Any) -> dict[str, Any]:
    total = len(fields)
    if total == 0:
        return _score_signal(0.0, False, "missing")
    filled = sum(1 for value in fields.values() if _is_present(value))
    return _score_signal(filled / total, True, f"{filled}/{total}")


def _score_extra_data_richness(extra_data: Any) -> dict[str, Any]:
    data = _normalize_extra_data(extra_data)
    if not data:
        return _score_signal(0.0, False, "missing")

    lots = data.get("lots")
    documents = data.get("documents")
    has_lots = isinstance(lots, list) and len(lots) > 0
    has_documents = isinstance(documents, list) and len(documents) > 0
    has_pdf = _is_present(data.get("pdf_url")) or _is_present(data.get("has_pdf")) or has_documents

    fields = {
        "procedure": data.get("procedure"),
        "financement": data.get("financement"),
        "type_commande": data.get("type_commande"),
        "region_execution": data.get("region_execution"),
        "full_address": data.get("full_address"),
        "caution": data.get("caution"),
        "lots": lots if has_lots else None,
        "documents": documents if has_documents else None,
        "pdf_url": data.get("pdf_url") if has_pdf else None,
        "cahier_des_charges_url": data.get("cahier_des_charges_url"),
    }
    filled = sum(1 for value in fields.values() if _is_present(value))
    score = min(1.0, filled / 6)
    return _score_signal(score, True, f"{filled}/{len(fields)}")


def _score_skill_alignment(skills: Any, description: Any) -> dict[str, Any]:
    skill_items = _clean_list(skills)
    description_text = _normalize_text(description)
    if not skill_items or not description_text:
        return _score_signal(0.0, False, "missing")

    normalized_skills = [_normalize_text(skill) for skill in skill_items if _normalize_text(skill)]
    if not normalized_skills:
        return _score_signal(0.0, False, "missing")

    hits = sum(1 for skill in normalized_skills if skill in description_text)
    return _score_signal(hits / len(normalized_skills), True, "aligned")


def _score_freshness(date_publication: Any) -> dict[str, Any]:
    if not date_publication:
        return _score_signal(0.0, False, "missing")

    try:
        if isinstance(date_publication, str):
            date_publication = datetime.fromisoformat(date_publication.replace("Z", "+00:00")).date()
        days = (datetime.now().date() - date_publication).days
    except Exception:
        return _score_signal(0.5, True, "unknown")

    if days <= 3:
        return _score_signal(1.0, True, "fresh")
    if days <= 7:
        return _score_signal(0.9, True, "recent")
    if days <= 30:
        return _score_signal(0.7, True, "current")
    if days <= 90:
        return _score_signal(0.4, True, "aging")
    return _score_signal(0.2, True, "stale")


def _score_consistency(title: Any, description: Any) -> dict[str, Any]:
    title_words = set(_normalize_text(title).split())
    description_words = set(_normalize_text(description).split())
    if not title_words or not description_words:
        return _score_signal(0.0, False, "missing")
    overlap = len(title_words & description_words) / max(len(title_words), 1)
    return _score_signal(overlap, True, "overlap")


def _normalize_extra_data(extra_data: Any) -> dict[str, Any]:
    return extra_data if isinstance(extra_data, dict) else {}


def _is_project_type(type_value: Any) -> bool:
    text = _normalize_text(type_value)
    return any(marker in text for marker in PROJECT_TYPE_MARKERS)


def _compute_project_bonus(
    *,
    organisation_nom: Any,
    date_publication: Any,
    date_limite: Any,
    extra_data: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    lots = extra_data.get("lots")
    documents = extra_data.get("documents")
    has_documents = isinstance(documents, list) and len(documents) > 0
    has_pdf = _is_present(extra_data.get("pdf_url")) or _is_present(extra_data.get("has_pdf")) or has_documents
    is_urgent = bool(extra_data.get("is_urgent"))
    bonus_details = {
        "organization": 0.1 if _is_present(organisation_nom) else 0.0,
        "date_publication": 0.1 if _is_present(date_publication) else 0.0,
        "deadline": 0.1 if _is_present(date_limite) else 0.0,
        "procedure": 0.05 if _is_present(extra_data.get("procedure")) else 0.0,
        "financement": 0.05 if _is_present(extra_data.get("financement")) else 0.0,
        "type_commande": 0.05 if _is_present(extra_data.get("type_commande")) else 0.0,
        "lots": 0.15 if isinstance(lots, list) and len(lots) > 0 else 0.0,
        "documents": 0.1 if has_pdf else 0.0,
        "urgency": 0.05 if is_urgent else 0.0,
    }
    return sum(bonus_details.values()), bonus_details


def _build_signals(
    *,
    organisation_nom: Any,
    ville: Any,
    description: Any,
    source_item_url: Any,
    date_confidence: Any,
    titre: Any,
    skills: Any,
    date_publication: Any,
    date_limite: Any,
    extra_data: dict[str, Any],
    contract_type: Any,
    availability: Any,
    education_level: Any,
    is_project: bool,
) -> dict[str, dict[str, Any]]:
    if is_project:
        completeness = _score_completeness(
            titre=titre,
            organisation_nom=organisation_nom,
            ville=ville,
            description=description,
            source_item_url=source_item_url,
            date_limite=date_limite,
            procedure=extra_data.get("procedure"),
            financement=extra_data.get("financement"),
            region_execution=extra_data.get("region_execution"),
            lots=extra_data.get("lots"),
            pdf_url=extra_data.get("pdf_url"),
        )
        return {
            "organization": _score_organization(organisation_nom),
            "description": _score_description(description),
            "location": _score_location(ville or extra_data.get("region_execution")),
            "url": _score_url(source_item_url),
            "date": _score_date_confidence(date_confidence),
            "title": _score_title(titre),
            "completeness": completeness,
            "extra_data": _score_extra_data_richness(extra_data),
            "freshness": _score_freshness(date_publication),
        }

    completeness = _score_completeness(
        titre=titre,
        organisation_nom=organisation_nom,
        ville=ville,
        description=description,
        source_item_url=source_item_url,
        contract_type=contract_type,
        availability=availability,
        education_level=education_level,
        skills=skills,
    )
    return {
        "organization": _score_organization(organisation_nom),
        "description": _score_description(description),
        "location": _score_location(ville),
        "url": _score_url(source_item_url),
        "date": _score_date_confidence(date_confidence),
        "skills": _score_skills(skills),
        "title": _score_title(titre),
        "completeness": completeness,
        "skill_alignment": _score_skill_alignment(skills, description),
        "freshness": _score_freshness(date_publication),
        "consistency": _score_consistency(titre, description),
    }


def _score_with_dynamic_weights(
    signals: dict[str, dict[str, Any]],
    base_weights: dict[str, float],
) -> tuple[float, dict[str, float]]:
    weighted_total = 0.0
    total_weight = 0.0
    effective_weights: dict[str, float] = {}

    for signal_name, base_weight in base_weights.items():
        signal = signals.get(signal_name)
        if not signal or not signal.get("available"):
            weighted_total += base_weight * MISSING_SIGNAL_SCORE
            total_weight += base_weight
            effective_weights[signal_name] = float(base_weight)
            continue
        weighted_total += base_weight * float(signal["score"])
        total_weight += base_weight
        effective_weights[signal_name] = float(base_weight)

    score = weighted_total / total_weight if total_weight else 0.0
    return score, effective_weights


def compute_quality_score_v4(
    *,
    organisation_nom: Any = "",
    ville: Any = "",
    description: Any = "",
    source_item_url: Any = "",
    date_confidence: Any = "",
    titre: Any = "",
    skills: Any = None,
    source_name: Any = "",
    description_html: Any = "",
    contract_type: Any = "",
    availability: Any = "",
    education_level: Any = "",
    date_publication: Any = None,
    date_limite: Any = None,
    type_opportunite: Any = "",
    extra_data: Any = None,
    debug: bool = False,
) -> Any:
    del description_html

    normalized_extra_data = _normalize_extra_data(extra_data)
    is_project = _is_project_type(type_opportunite)
    signals = _build_signals(
        organisation_nom=organisation_nom,
        ville=ville,
        description=description,
        source_item_url=source_item_url,
        date_confidence=date_confidence,
        titre=titre,
        skills=skills,
        date_publication=date_publication,
        date_limite=date_limite,
        extra_data=normalized_extra_data,
        contract_type=contract_type,
        availability=availability,
        education_level=education_level,
        is_project=is_project,
    )

    base_weights = PROJECT_SIGNAL_WEIGHTS if is_project else JOB_SIGNAL_WEIGHTS
    score, effective_weights = _score_with_dynamic_weights(signals, base_weights)

    if not is_project and signals.get("skills", {}).get("score", 0.0) > 0.7 and signals.get("description", {}).get("score", 0.0) < 0.4:
        score *= 0.85

    source_reliability = SOURCE_RELIABILITY.get(_as_text(source_name), 1.0)
    source_multiplier = 1 + (source_reliability - 1) * 0.15

    project_bonus = 0.0
    project_bonus_details: dict[str, float] = {}
    if is_project:
        project_bonus, project_bonus_details = _compute_project_bonus(
            organisation_nom=organisation_nom,
            date_publication=date_publication,
            date_limite=date_limite,
            extra_data=normalized_extra_data,
        )
        score = 0.65 * score + 0.35 * project_bonus
    else:
        score *= source_multiplier

    penalty = 1.0
    if not _is_present(organisation_nom):
        penalty *= 0.85
    if not _is_present(ville):
        penalty *= 0.9
    if not _is_present(description) or len(_as_text(description)) < 80:
        penalty *= 0.8
    if not is_project and not _clean_list(skills):
        penalty *= 0.9

    score = round(max(0.0, min(score * penalty, 1.0)), 4)

    if not debug:
        return score

    return {
        "score": score,
        "details": {name: round(signal["score"], 4) for name, signal in signals.items()},
        "available": {name: bool(signal["available"]) for name, signal in signals.items()},
        "reasons": {name: signal["reason"] for name, signal in signals.items()},
        "weights": {name: round(effective_weights.get(name, 0.0), 4) for name in base_weights},
        "source_multiplier": round(source_multiplier if not is_project else 1.0, 4),
        "project_bonus": round(project_bonus, 4),
        "project_bonus_details": project_bonus_details,
    }


def compute_quality_score_v3(**kwargs: Any) -> Any:
    return compute_quality_score_v4(**kwargs)


def compute_quality_score(**kwargs: Any) -> Any:
    return compute_quality_score_v4(**kwargs)
