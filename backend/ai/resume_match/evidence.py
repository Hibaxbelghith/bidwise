from __future__ import annotations

import re
import unicodedata
from typing import Any

from ai.user_features import build_user_features


MAX_TEXT_EXCERPT_CHARS = 2600
MAX_ITEMS = 12
SENIORITY_ORDER = {"DEBUTANT": 0, "JUNIOR": 1, "CONFIRME": 2, "SENIOR": 3}
SENIORITY_REVIEW_KEYWORDS = {
    "senior",
    "lead",
    "manager",
    "responsable",
    "expert",
    "architect",
    "architecte",
    "confirme",
    "confirmé",
    "experimente",
    "expérimenté",
    "chef",
    "coordinateur",
    "principal",
    "staff",
    "superviseur",
}

READY_STATUS = "READY"
NO_RESUME_STATUS = "NO_RESUME"
RESUME_PROCESSING_STATUS = "RESUME_PROCESSING"
RESUME_NOT_READY_STATUS = "RESUME_NOT_READY"
_LOW_VALUE_KEYWORDS = frozenset(
    {
        "equipe",
        "travail",
        "poste",
        "profil",
        "candidat",
        "entreprise",
        "societe",
        "motivated",
        "dynamique",
        "rigoureux",
        "serieux",
        "autonome",
        "organise",
        "disponible",
        "polyvalent",
        "proactif",
        "esprit",
        "sens",
        "capacite",
        "aptitude",
    }
)


def build_resume_match_evidence(*, user: Any | None = None, profile: Any | None = None, opportunity: Any) -> dict[str, Any]:
    """
    Build a rich deterministic evidence payload for the resume match assistant.

    This service intentionally reuses the existing ProfileResume/Profile features
    and opportunity enrichment data. It does not parse resumes, call an LLM, or
    mutate recommendation state.
    """
    profile = profile or getattr(user, "profil", None)
    if profile is None:
        return {
            "has_resume": False,
            "status": NO_RESUME_STATUS,
            "resume_status": "",
            "profile": {},
            "resume": {},
            "opportunity": _opportunity_payload(opportunity),
            "match": _empty_match_payload(),
            "qwen_context": {},
        }

    active_resume = _get_active_resume(profile)
    features = build_user_features(profile)
    profile_payload = _profile_payload(profile, features)
    opportunity_payload = _opportunity_payload(opportunity)

    if active_resume is None:
        return {
            "has_resume": False,
            "status": NO_RESUME_STATUS,
            "resume_status": "",
            "profile": profile_payload,
            "resume": {},
            "opportunity": opportunity_payload,
            "match": _empty_match_payload(),
            "qwen_context": _qwen_context(profile_payload, {}, opportunity_payload, _empty_match_payload()),
        }

    resume_payload = _resume_payload(active_resume)
    readiness = _resume_readiness(active_resume)
    if readiness["status"] != READY_STATUS:
        match_payload = _empty_match_payload()
        return {
            "has_resume": True,
            "status": readiness["status"],
            "resume_status": readiness["resume_status"],
            "profile": profile_payload,
            "resume": resume_payload,
            "opportunity": opportunity_payload,
            "match": match_payload,
            "qwen_context": _qwen_context(profile_payload, resume_payload, opportunity_payload, match_payload),
        }

    match_payload = _build_match_payload(
        profile_payload=profile_payload,
        resume_payload=resume_payload,
        opportunity_payload=opportunity_payload,
    )
    return {
        "has_resume": True,
        "status": READY_STATUS,
        "resume_status": readiness["resume_status"],
        "profile": profile_payload,
        "resume": resume_payload,
        "opportunity": opportunity_payload,
        "match": match_payload,
        "qwen_context": _qwen_context(profile_payload, resume_payload, opportunity_payload, match_payload),
    }


def _get_active_resume(profile: Any) -> Any | None:
    resumes = getattr(profile, "resumes", None)
    if resumes is None:
        return None
    if hasattr(resumes, "filter"):
        return resumes.filter(is_active=True).order_by("-uploaded_at", "-id").first()
    if isinstance(resumes, (list, tuple)):
        for resume in resumes:
            if getattr(resume, "is_active", False):
                return resume
    return None


def _resume_readiness(resume: Any) -> dict[str, str]:
    parsing_status = str(getattr(resume, "parsing_status", "") or "").upper()
    semantic_status = str(getattr(resume, "semantic_resume_status", "") or "").upper()
    combined = f"{parsing_status}/{semantic_status}".strip("/")

    if parsing_status in {"PENDING", "PROCESSING"} or semantic_status in {"PENDING", "PROCESSING"}:
        return {"status": RESUME_PROCESSING_STATUS, "resume_status": combined}
    if parsing_status == "SUCCEEDED" and semantic_status == "SUCCEEDED":
        return {"status": READY_STATUS, "resume_status": combined}
    return {"status": RESUME_NOT_READY_STATUS, "resume_status": combined}


def _profile_payload(profile: Any, features: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": getattr(profile, "id", None),
        "target_roles": _clean_list(features.get("target_roles") or features.get("roles")),
        "skills": _clean_list(features.get("profile_skills") or features.get("skills")),
        "all_skills": _clean_list(features.get("skills")),
        "interests": _clean_list(features.get("interests")),
        "experience_level": str(features.get("experience_level") or "").strip(),
        "experience_years": features.get("experience_years"),
        "locations": _clean_list(features.get("locations")),
        "work_modes": _clean_list(features.get("work_modes")),
        "employment_types": _clean_list(features.get("employment_types")),
        "salary": {
            "expected": features.get("salary"),
            "min": features.get("salary_min"),
            "max": features.get("salary_max"),
            "currency": str(features.get("salary_currency") or "").strip(),
            "period": str(features.get("salary_period") or "").strip(),
        },
        "semantic_resume_role": str(features.get("semantic_resume_canonical_role") or "").strip(),
        "semantic_resume_target_roles": _clean_list(features.get("semantic_resume_target_roles")),
    }


def _resume_payload(resume: Any) -> dict[str, Any]:
    metadata = getattr(resume, "semantic_resume_metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    parsed_text = str(getattr(resume, "parsed_text", "") or "").strip()
    resume_source = str(getattr(resume, "resume_text_embedding_source", "") or "").strip() or parsed_text
    return {
        "id": getattr(resume, "id", None),
        "source_type": str(getattr(resume, "source_type", "") or "").strip(),
        "parsing_status": str(getattr(resume, "parsing_status", "") or "").strip(),
        "semantic_status": str(getattr(resume, "semantic_resume_status", "") or "").strip(),
        "semantic_confidence": _safe_float(getattr(resume, "semantic_resume_confidence", 0.0)),
        "skills": _clean_list(getattr(resume, "extracted_skills", [])),
        "tools": _clean_list(getattr(resume, "extracted_tools", [])),
        "domains": _clean_list(getattr(resume, "extracted_domains", [])),
        "languages": _clean_list(getattr(resume, "extracted_languages", [])),
        "canonical_role": str(metadata.get("canonical_role") or "").strip(),
        "target_roles": _clean_list(metadata.get("target_roles")),
        "business_families": _clean_list(metadata.get("business_families")),
        "family_confidence": _safe_float(metadata.get("family_confidence")),
        "summary_excerpt": _excerpt(resume_source),
        "has_text": bool(parsed_text),
        "updated_at": _iso_value(getattr(resume, "semantic_resume_updated_at", None) or getattr(resume, "parsed_at", None)),
    }


def _opportunity_payload(opportunity: Any) -> dict[str, Any]:
    extra_data = getattr(opportunity, "extra_data", {}) or {}
    if not isinstance(extra_data, dict):
        extra_data = {}
    enrichment = extra_data.get("llm_enrichment") or {}
    if not isinstance(enrichment, dict):
        enrichment = {}

    skills = _merge_unique(
        getattr(opportunity, "skills", []),
        getattr(opportunity, "raw_skills", []),
        enrichment.get("skills"),
    )
    tools = _clean_list(enrichment.get("tools"))
    domains = _clean_list(enrichment.get("domains"))
    responsibilities = _clean_list(enrichment.get("responsibilities"))
    requirements = _clean_list(enrichment.get("requirements"))

    return {
        "id": getattr(opportunity, "id", None),
        "title": str(getattr(opportunity, "titre", "") or "").strip(),
        "company": str(getattr(opportunity, "organisation_nom", "") or "").strip(),
        "source": str(getattr(getattr(opportunity, "source", None), "nom", "") or "").strip(),
        "location": str(getattr(opportunity, "ville", "") or "").strip(),
        "contract": str(getattr(opportunity, "contract_type", "") or "").strip(),
        "work_mode": str(getattr(opportunity, "normalized_work_mode", "") or "").strip(),
        "salary": str(getattr(opportunity, "salary", "") or "").strip(),
        "experience": {
            "min": getattr(opportunity, "experience_min", None),
            "max": getattr(opportunity, "experience_max", None),
            "years": getattr(opportunity, "experience_years", None),
        },
        "education": str(getattr(opportunity, "education_level", "") or "").strip(),
        "skills": skills[:MAX_ITEMS],
        "tools": tools[:MAX_ITEMS],
        "domains": domains[:MAX_ITEMS],
        "responsibilities": responsibilities[:MAX_ITEMS],
        "requirements": requirements[:MAX_ITEMS],
        "canonical_role": str(enrichment.get("canonical_role") or "").strip(),
        "target_roles": _clean_list(enrichment.get("target_roles")),
        "business_families": _clean_list(enrichment.get("business_families")),
        "description_excerpt": _excerpt(getattr(opportunity, "description", "")),
        "published_at": _iso_value(getattr(opportunity, "date_publication", None)),
        "updated_at": _iso_value(getattr(opportunity, "date_modification", None)),
        "skills_source": str(enrichment.get("skills_source") or "").strip(),
    }


def _build_match_payload(
    *,
    profile_payload: dict[str, Any],
    resume_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
) -> dict[str, Any]:
    ats_resume_keywords = _resume_ats_keyword_values(profile_payload, resume_payload)
    opportunity_keywords = _opportunity_ats_keyword_values(opportunity_payload)
    matching_keywords = _matching_values(ats_resume_keywords, opportunity_keywords)
    missing_keywords = _missing_values(ats_resume_keywords, opportunity_keywords)
    prioritized_gaps = _prioritize_missing_keywords(missing_keywords, opportunity_payload)

    role_alignment = _role_alignment(profile_payload, resume_payload, opportunity_payload)
    seniority_alignment = _seniority_alignment(profile_payload, opportunity_payload)
    location_alignment = _location_alignment(profile_payload, opportunity_payload)
    contract_alignment = _contract_alignment(profile_payload, opportunity_payload)
    keyword_coverage = _coverage_ratio(matching_keywords, opportunity_keywords)
    fit_score = _fit_score(
        role_alignment=role_alignment,
        seniority_alignment=seniority_alignment,
        location_alignment=location_alignment,
        contract_alignment=contract_alignment,
        keyword_coverage=keyword_coverage,
        resume_confidence=resume_payload.get("semantic_confidence"),
    )
    verdict = _verdict(fit_score)
    strong_fit = _strong_fit_evidence(
        role_alignment=role_alignment,
        seniority_alignment=seniority_alignment,
        location_alignment=location_alignment,
        contract_alignment=contract_alignment,
        matching_keywords=matching_keywords,
        opportunity_payload=opportunity_payload,
    )
    watch_outs = _watch_outs(
        role_alignment=role_alignment,
        seniority_alignment=seniority_alignment,
        missing_keywords=missing_keywords,
        keyword_coverage=keyword_coverage,
        resume_payload=resume_payload,
        opportunity_payload=opportunity_payload,
    )

    return {
        "fit_score": fit_score,
        "verdict": verdict,
        "role_alignment": role_alignment,
        "seniority_alignment": seniority_alignment,
        "location_alignment": location_alignment,
        "contract_alignment": contract_alignment,
        "matching_skills": _matching_values(
            ats_resume_keywords,
            opportunity_payload.get("skills", []),
        )[:MAX_ITEMS],
        "matching_keywords": matching_keywords[:MAX_ITEMS],
        "missing_keywords": missing_keywords[:MAX_ITEMS],
        "prioritized_gaps": prioritized_gaps,
        "keyword_coverage": keyword_coverage,
        "where_strong_fit": strong_fit[:5],
        "what_to_watch_out_for": watch_outs[:5],
        "ats": {
            "keyword_coverage_percent": int(round(keyword_coverage * 100)),
            "covered_keywords": matching_keywords[:MAX_ITEMS],
            "missing_or_weak_keywords": missing_keywords[:MAX_ITEMS],
            "resume_text_available": bool(resume_payload.get("has_text")),
            "semantic_resume_confidence": resume_payload.get("semantic_confidence", 0.0),
        },
        "next_step_hints": _next_step_hints(verdict, missing_keywords, watch_outs),
    }


def _empty_match_payload() -> dict[str, Any]:
    return {
        "fit_score": 0,
        "verdict": "resume_required",
        "role_alignment": {"level": "unknown", "reason": "Resume evidence is not ready."},
        "seniority_alignment": {"level": "unknown", "reason": ""},
        "location_alignment": {"level": "unknown", "reason": ""},
        "contract_alignment": {"level": "unknown", "reason": ""},
        "matching_skills": [],
        "matching_keywords": [],
        "missing_keywords": [],
        "prioritized_gaps": {"critical": [], "useful": [], "optional": []},
        "keyword_coverage": 0.0,
        "where_strong_fit": [],
        "what_to_watch_out_for": [],
        "ats": {
            "keyword_coverage_percent": 0,
            "covered_keywords": [],
            "missing_or_weak_keywords": [],
            "resume_text_available": False,
            "semantic_resume_confidence": 0.0,
        },
        "next_step_hints": [],
    }


def _resume_ats_keyword_values(profile_payload: dict[str, Any], resume_payload: dict[str, Any]) -> list[str]:
    cv_keywords = _merge_unique(
        resume_payload.get("skills"),
        resume_payload.get("tools"),
    )
    if cv_keywords:
        return cv_keywords
    return _merge_unique(
        profile_payload.get("skills"),
        profile_payload.get("all_skills"),
    )


def _opportunity_ats_keyword_values(opportunity_payload: dict[str, Any]) -> list[str]:
    return _merge_unique(
        opportunity_payload.get("skills"),
        opportunity_payload.get("tools"),
        opportunity_payload.get("domains"),
    )


def _role_alignment(profile_payload: dict[str, Any], resume_payload: dict[str, Any], opportunity_payload: dict[str, Any]) -> dict[str, str]:
    profile_roles = _merge_unique(
        profile_payload.get("target_roles"),
        profile_payload.get("semantic_resume_role"),
        profile_payload.get("semantic_resume_target_roles"),
        resume_payload.get("canonical_role"),
        resume_payload.get("target_roles"),
    )
    opportunity_roles = _merge_unique(
        opportunity_payload.get("canonical_role"),
        opportunity_payload.get("target_roles"),
        opportunity_payload.get("title"),
    )
    matches = _matching_values(profile_roles, opportunity_roles)
    if matches:
        return {
            "level": "strong",
            "reason": f"Role evidence overlaps with the opportunity: {', '.join(matches[:3])}.",
        }
    if _has_token_overlap(profile_roles, opportunity_roles):
        return {
            "level": "related",
            "reason": "The resume/profile role is related to the opportunity, but not an exact title match.",
        }
    return {
        "level": "unclear",
        "reason": "The resume does not clearly show the target role requested by this opportunity.",
    }


def _seniority_alignment(profile_payload: dict[str, Any], opportunity_payload: dict[str, Any]) -> dict[str, str]:
    profile_years = _safe_int(profile_payload.get("experience_years"))
    profile_level = str(profile_payload.get("experience_level") or "").strip().upper()
    exp = opportunity_payload.get("experience") or {}
    opp_min = _safe_int(exp.get("min") or exp.get("years"))
    opp_max = _safe_int(exp.get("max"))
    title = f"{opportunity_payload.get('title', '')} {' '.join(opportunity_payload.get('requirements', []))}".lower()
    profile_rank = SENIORITY_ORDER.get(profile_level)

    if any(word in title for word in SENIORITY_REVIEW_KEYWORDS):
        if profile_level == "JUNIOR" or profile_rank in {SENIORITY_ORDER["DEBUTANT"], SENIORITY_ORDER["JUNIOR"]}:
            return {
                "level": "watch",
                "reason": "The opportunity appears more senior than the current profile evidence.",
            }

    if profile_years is not None and opp_min is not None and profile_years < opp_min:
        return {
            "level": "watch",
            "reason": f"The role asks for around {opp_min}+ years while the profile shows {profile_years} years.",
        }
    if profile_years is not None and (opp_min is not None or opp_max is not None):
        return {"level": "compatible", "reason": "Experience evidence appears compatible with the listed range."}
    if profile_rank is not None:
        return {"level": "compatible", "reason": f"Profile seniority is available: {profile_level}."}
    return {"level": "unknown", "reason": "Resume seniority evidence is not explicit."}


def _location_alignment(profile_payload: dict[str, Any], opportunity_payload: dict[str, Any]) -> dict[str, str]:
    locations = profile_payload.get("locations") or []
    opportunity_location = str(opportunity_payload.get("location") or "").strip()
    if not opportunity_location:
        return {"level": "unknown", "reason": "Opportunity location is not specified."}
    if not locations:
        return {"level": "unknown", "reason": "Profile location preferences are not specified."}
    if _normalize(opportunity_location) in {_normalize(value) for value in locations}:
        return {"level": "aligned", "reason": f"Location aligned: {opportunity_location}."}
    return {"level": "watch", "reason": f"Opportunity is in {opportunity_location}, outside listed preferences."}


def _contract_alignment(profile_payload: dict[str, Any], opportunity_payload: dict[str, Any]) -> dict[str, str]:
    contracts = profile_payload.get("employment_types") or []
    opportunity_contract = str(opportunity_payload.get("contract") or "").strip()
    if not opportunity_contract:
        return {"level": "unknown", "reason": "Opportunity contract is not specified."}
    if not contracts:
        return {"level": "unknown", "reason": "Profile contract preferences are not specified."}
    if _has_token_overlap(contracts, [opportunity_contract]):
        return {"level": "aligned", "reason": f"Contract preference appears compatible: {opportunity_contract}."}
    return {"level": "review", "reason": f"Contract should be reviewed: {opportunity_contract}."}


def _fit_score(
    *,
    role_alignment: dict[str, str],
    seniority_alignment: dict[str, str],
    location_alignment: dict[str, str],
    contract_alignment: dict[str, str],
    keyword_coverage: float,
    resume_confidence: Any,
) -> int:
    score = 0.0
    score += {"strong": 35, "related": 20, "unclear": 6}.get(role_alignment.get("level"), 4)
    score += min(28.0, max(0.0, keyword_coverage) * 28.0)
    score += {"compatible": 15, "unknown": 7, "watch": 3}.get(seniority_alignment.get("level"), 5)
    score += {"aligned": 8, "unknown": 4, "watch": 2}.get(location_alignment.get("level"), 4)
    score += {"aligned": 5, "unknown": 3, "review": 2}.get(contract_alignment.get("level"), 3)
    score += min(10.0, max(0.0, _safe_float(resume_confidence)) * 10.0)
    return int(round(max(0.0, min(100.0, score))))


def _verdict(score: int) -> str:
    if score >= 78:
        return "strong_match"
    if score >= 62:
        return "good_match"
    if score >= 45:
        return "partial_match"
    return "weak_match"


def _strong_fit_evidence(
    *,
    role_alignment: dict[str, str],
    seniority_alignment: dict[str, str],
    location_alignment: dict[str, str],
    contract_alignment: dict[str, str],
    matching_keywords: list[str],
    opportunity_payload: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if role_alignment.get("level") in {"strong", "related"}:
        items.append({"title": "Role alignment", "evidence": role_alignment.get("reason", "")})
    if matching_keywords:
        items.append({
            "title": "Relevant keywords",
            "evidence": f"Your resume already shows: {', '.join(matching_keywords[:6])}.",
        })
    if seniority_alignment.get("level") == "compatible":
        items.append({"title": "Experience fit", "evidence": seniority_alignment.get("reason", "")})
    if location_alignment.get("level") == "aligned":
        items.append({"title": "Location fit", "evidence": location_alignment.get("reason", "")})
    if contract_alignment.get("level") == "aligned":
        items.append({"title": "Contract fit", "evidence": contract_alignment.get("reason", "")})
    if opportunity_payload.get("skills_source") == "llm":
        items.append({
            "title": "AI-enriched job signals",
            "evidence": "The opportunity includes skills extracted from its description, improving match explainability.",
        })
    return items


def _watch_outs(
    *,
    role_alignment: dict[str, str],
    seniority_alignment: dict[str, str],
    missing_keywords: list[str],
    keyword_coverage: float,
    resume_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if role_alignment.get("level") == "unclear":
        items.append({"title": "Role evidence", "evidence": role_alignment.get("reason", "")})
    if seniority_alignment.get("level") == "watch":
        items.append({"title": "Seniority", "evidence": seniority_alignment.get("reason", "")})
    if missing_keywords:
        items.append({
            "title": "Missing or weak keywords",
            "evidence": f"Consider making these clearer if you have the experience: {', '.join(missing_keywords[:8])}.",
        })
    if keyword_coverage < 0.35 and opportunity_payload.get("skills"):
        items.append({
            "title": "ATS keyword coverage",
            "evidence": "The resume currently covers a limited share of the structured job keywords.",
        })
    if not resume_payload.get("has_text"):
        items.append({
            "title": "Resume text",
            "evidence": "The resume text is not available yet, so the analysis is limited.",
        })
    return items


def _next_step_hints(verdict: str, missing_keywords: list[str], watch_outs: list[dict[str, str]]) -> list[str]:
    hints = []
    if verdict in {"strong_match", "good_match"}:
        hints.append("Tailor the resume summary around the strongest role and skill evidence before applying.")
    else:
        hints.append("Review the role requirements carefully before applying.")
    if missing_keywords:
        hints.append("Add missing keywords only if they reflect real experience.")
    if watch_outs:
        hints.append("Address the watch-out points in the CV or cover letter.")
    return hints[:3]


def _qwen_context(
    profile_payload: dict[str, Any],
    resume_payload: dict[str, Any],
    opportunity_payload: dict[str, Any],
    match_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "instruction": (
            "Use only this structured evidence. Do not invent experience, salary, "
            "certifications, tools, or achievements not present in the resume/profile."
        ),
        "profile": {
            "target_roles": profile_payload.get("target_roles", []),
            "skills": profile_payload.get("all_skills", []),
            "experience_level": profile_payload.get("experience_level", ""),
            "experience_years": profile_payload.get("experience_years"),
        },
        "resume": {
            "skills": resume_payload.get("skills", []),
            "tools": resume_payload.get("tools", []),
            "domains": resume_payload.get("domains", []),
            "canonical_role": resume_payload.get("canonical_role", ""),
            "summary_excerpt": resume_payload.get("summary_excerpt", ""),
        },
        "opportunity": {
            "title": opportunity_payload.get("title", ""),
            "company": opportunity_payload.get("company", ""),
            "skills": opportunity_payload.get("skills", []),
            "requirements": opportunity_payload.get("requirements", []),
            "responsibilities": opportunity_payload.get("responsibilities", []),
            "description_excerpt": opportunity_payload.get("description_excerpt", ""),
            "salary": opportunity_payload.get("salary", ""),
        },
        "match": match_payload,
        "required_response_structure": [
            "Summary",
            "Where you are a strong fit",
            "What to watch out for",
            "Missing or weak keywords",
            "Next step",
        ],
    }


def _matching_values(source_values: list[str], target_values: list[str]) -> list[str]:
    source = _labeled_map(source_values)
    matches = []
    for label in _clean_list(target_values):
        key = _normalize(label)
        if not key:
            continue
        if key in source or _has_token_overlap(source.keys(), [label]):
            matches.append(label)
    return _dedupe(matches)


def _missing_values(source_values: list[str], target_values: list[str]) -> list[str]:
    matched_keys = {_normalize(value) for value in _matching_values(source_values, target_values)}
    missing = []
    source_keys = set(_labeled_map(source_values).keys())
    for label in _clean_list(target_values):
        key = _normalize(label)
        if not key or key in matched_keys:
            continue
        if key in source_keys or _has_token_overlap(source_keys, [label]):
            continue
        if _is_low_value_keyword(label):
            continue
        missing.append(label)
    return _dedupe(missing)


def _prioritize_missing_keywords(
    missing_keywords: list[str],
    opportunity_payload: dict[str, Any],
) -> dict[str, list[str]]:
    if not missing_keywords:
        return {"critical": [], "useful": [], "optional": []}

    contexts = {
        "skills": _clean_list(opportunity_payload.get("skills")),
        "requirements": _clean_list(opportunity_payload.get("requirements")),
        "responsibilities": _clean_list(opportunity_payload.get("responsibilities")),
        "description": [str(opportunity_payload.get("description_excerpt") or "").strip()],
    }

    scored = []
    for index, keyword in enumerate(_clean_list(missing_keywords)):
        score = _gap_context_score(keyword, contexts) + _gap_specificity_weight(keyword)
        scored.append({"keyword": keyword, "score": score, "index": index})

    scored.sort(key=lambda item: (-item["score"], item["index"]))

    result = {"critical": [], "useful": [], "optional": []}
    for position, item in enumerate(scored):
        result[_gap_tier(item["score"], position)].append(item["keyword"])

    return {tier: values[:MAX_ITEMS] for tier, values in result.items()}


def _gap_context_score(keyword: str, contexts: dict[str, list[str]]) -> int:
    score = 0
    if _keyword_appears(keyword, contexts.get("skills", [])):
        score += 45
    if _keyword_appears(keyword, contexts.get("requirements", [])):
        score += 35
    if _keyword_appears(keyword, contexts.get("responsibilities", [])):
        score += 25
    score += min(15, _keyword_hit_count(keyword, contexts.get("description", [])) * 5)
    return score


def _gap_specificity_weight(keyword: str) -> int:
    if _is_low_value_keyword(keyword):
        return -10

    key = _normalize(keyword)
    weight = 0
    if len(key.split()) >= 2:
        weight += 14
    if any(separator in str(keyword) for separator in ("/", "-", ".", "+")):
        weight += 10
    if len(key) >= 10:
        weight += 6
    if any(char.isdigit() for char in str(keyword)):
        weight += 4
    return weight


def _gap_tier(score: int, position: int) -> str:
    if score >= 55 or position < 3:
        return "critical"
    if score >= 25 or position < 6:
        return "useful"
    return "optional"


def _keyword_appears(keyword: str, values: list[str]) -> bool:
    key = _normalize(keyword)
    if not key:
        return False
    return any(key in _normalize(value) for value in values)


def _keyword_hit_count(keyword: str, values: list[str]) -> int:
    key = _normalize(keyword)
    if not key:
        return 0
    return sum(_normalize(value).count(key) for value in values)


def _coverage_ratio(matches: list[str], target_values: list[str]) -> float:
    target_count = len([value for value in _clean_list(target_values) if not _is_low_value_keyword(value)])
    if target_count <= 0:
        return 0.0
    return round(min(1.0, len(_dedupe(matches)) / target_count), 4)


def _has_token_overlap(source_values: Any, target_values: Any) -> bool:
    source_tokens = set()
    for value in _clean_list(source_values):
        source_tokens.update(_tokens(value))
    for value in _clean_list(target_values):
        target_tokens = _tokens(value)
        if not target_tokens:
            continue
        common = source_tokens.intersection(target_tokens)
        if len(common) >= min(2, len(target_tokens)):
            return True
    return False


def _labeled_map(values: Any) -> dict[str, str]:
    mapped = {}
    for value in _clean_list(values):
        key = _normalize(value)
        if key and key not in mapped:
            mapped[key] = value
    return mapped


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", _normalize(value))
        if len(token) >= 3 or token in {"qa", "ui", "ux", "bi", "ai"}
    }


def _normalize(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9+#./-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = [value]
    return _dedupe(str(item).strip() for item in raw_items if str(item or "").strip())


def _merge_unique(*values: Any) -> list[str]:
    merged = []
    for value in values:
        merged.extend(_clean_list(value))
    return _dedupe(merged)


def _dedupe(values: Any) -> list[str]:
    result = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = _normalize(text)
        if not text or not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _is_low_value_keyword(value: Any) -> bool:
    return _normalize(value) in _LOW_VALUE_KEYWORDS


def _excerpt(value: Any, *, max_chars: int = MAX_TEXT_EXCERPT_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].strip() + "..."


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value or 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iso_value(value: Any) -> str:
    if not value:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
