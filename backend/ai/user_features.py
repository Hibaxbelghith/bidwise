def _clean_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = [value]

    cleaned = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _clean_positive_int(value):
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _merge_unique(*values):
    merged = []
    seen = set()
    for value in values:
        for item in _clean_list(value):
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _get_active_resume_parsed_text(profile):
    active_resume = _get_active_resume(profile)
    return _clean_text(getattr(active_resume, "parsed_text", "")) if active_resume else ""


def _get_active_resume(profile):
    resumes = getattr(profile, "resumes", None)
    if resumes is None:
        return None

    if hasattr(resumes, "filter"):
        return (
            resumes
            .filter(is_active=True)
            .only(
                "profile_id",
                "parsed_text",
                "extracted_skills",
                "extracted_domains",
                "extracted_tools",
                "extracted_languages",
                "semantic_resume_confidence",
                "semantic_resume_status",
                "semantic_resume_metadata",
            )
            .first()
        )

    if isinstance(resumes, (list, tuple)):
        for resume in resumes:
            if getattr(resume, "is_active", False):
                return resume

    return None


def _semantic_signals_from_resume(active_resume):
    empty = {
        "skills": [],
        "domains": [],
        "tools": [],
        "languages": [],
        "confidence": 0.0,
        "business_families": [],
        "family_confidence": 0.0,
        "canonical_role": "",
        "target_roles": [],
    }
    if not active_resume:
        return empty
    if str(getattr(active_resume, "semantic_resume_status", "") or "").upper() != "SUCCEEDED":
        return empty

    try:
        confidence = float(getattr(active_resume, "semantic_resume_confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    metadata = getattr(active_resume, "semantic_resume_metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    try:
        family_confidence = float(metadata.get("family_confidence") or 0.0)
    except (TypeError, ValueError):
        family_confidence = 0.0

    return {
        "skills": _clean_list(getattr(active_resume, "extracted_skills", [])),
        "domains": _clean_list(getattr(active_resume, "extracted_domains", [])),
        "tools": _clean_list(getattr(active_resume, "extracted_tools", [])),
        "languages": _clean_list(getattr(active_resume, "extracted_languages", [])),
        "confidence": max(0.0, min(1.0, confidence)),
        "business_families": _clean_list(metadata.get("business_families")),
        "family_confidence": max(0.0, min(1.0, family_confidence)),
        "canonical_role": _clean_text(metadata.get("canonical_role")),
        "target_roles": _clean_list(metadata.get("target_roles")),
    }


def build_user_features(profile):
    """
    Convert a profile into a normalized ML feature dictionary.

    The function accepts current JSON-array fields and legacy comma-separated
    strings so callers can safely use it during and after data migrations.
    Missing or partial profile fields are normalized to empty strings/lists.
    """
    locations = _clean_list(getattr(profile, "preferred_locations", []))
    target_roles = _clean_list(getattr(profile, "target_roles", []))
    interests = _clean_list(getattr(profile, "domaines_interet", []))
    active_resume = _get_active_resume(profile)
    semantic_resume = _semantic_signals_from_resume(active_resume)
    semantic_resume_skills = _merge_unique(
        semantic_resume["skills"],
        semantic_resume["tools"],
    )
    features = {
        "profile_skills": _clean_list(getattr(profile, "competences", [])),
        "semantic_resume_skills": semantic_resume["skills"],
        "semantic_resume_domains": semantic_resume["domains"],
        "semantic_resume_tools": semantic_resume["tools"],
        "semantic_resume_languages": semantic_resume["languages"],
        "semantic_resume_confidence": semantic_resume["confidence"],
        "semantic_resume_business_families": semantic_resume["business_families"],
        "semantic_resume_family_confidence": semantic_resume["family_confidence"],
        "semantic_resume_canonical_role": semantic_resume["canonical_role"],
        "semantic_resume_target_roles": semantic_resume["target_roles"],
        "profile_business_families": semantic_resume["business_families"],
        "profile_family_confidence": semantic_resume["family_confidence"],
        "skills": _merge_unique(
            getattr(profile, "competences", []),
            semantic_resume_skills,
        ),
        "roles": _merge_unique(
            target_roles,
            semantic_resume["target_roles"],
            interests,
            semantic_resume["domains"],
        ),
        "target_roles": target_roles,
        "interests": _merge_unique(interests, semantic_resume["domains"]),
        "experience_level": _clean_text(getattr(profile, "niveau_experience", "")),
        "experience_years": _clean_positive_int(getattr(profile, "annees_experience", None)),
        "locations": locations,
        "location": locations[0] if locations else "",
        "remote": _clean_text(getattr(profile, "remote_preference", "")),
        "work_modes": _clean_list(getattr(profile, "work_mode_preferences", [])),
        "employment_types": _clean_list(getattr(profile, "employment_types", [])),
        "salary": _clean_positive_int(getattr(profile, "compensation_expectation", None)),
        "salary_min": _clean_positive_int(getattr(profile, "compensation_min_expectation", None)),
        "salary_max": _clean_positive_int(getattr(profile, "compensation_max_expectation", None)),
        "salary_currency": _clean_text(getattr(profile, "compensation_currency", "")),
        "salary_period": _clean_text(getattr(profile, "compensation_period", "")),
    }
    resume_text = _clean_text(getattr(active_resume, "parsed_text", "")) if active_resume else ""
    if resume_text:
        features["resume_text"] = resume_text
    return features
