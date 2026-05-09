from __future__ import annotations

from typing import Any


PROFILE_COMPLETION_WEIGHTS = (
    ("first_name", 7),
    ("last_name", 7),
    ("experience_level", 8),
    ("years_experience", 8),
    ("locations", 8),
    ("work_modes", 7),
    ("employment_types", 6),
    ("opportunity_types", 4),
    ("skills", 10),
    ("target_roles", 10),
    ("interests", 10),
    ("resume", 15),
)


def _has_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _has_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _has_active_resume(profile: Any) -> bool:
    prefetched = getattr(profile, "_prefetched_objects_cache", {}).get("resumes")
    if prefetched is not None:
        return any(getattr(resume, "is_active", False) for resume in prefetched)
    try:
        return profile.resumes.filter(is_active=True).exists()
    except Exception:
        return False


def calculate_profile_completion(profile: Any) -> dict[str, Any]:
    checks = {
        "first_name": _has_text(getattr(profile, "prenom", "")),
        "last_name": _has_text(getattr(profile, "nom", "")),
        "experience_level": _has_text(getattr(profile, "niveau_experience", "")),
        "years_experience": getattr(profile, "annees_experience", None) is not None,
        "locations": _has_list(getattr(profile, "preferred_locations", [])),
        "work_modes": _has_list(getattr(profile, "work_mode_preferences", [])),
        "employment_types": _has_list(getattr(profile, "employment_types", [])),
        "opportunity_types": _has_list(getattr(profile, "opportunity_types", [])),
        "skills": _has_list(getattr(profile, "competences", [])),
        "target_roles": _has_list(getattr(profile, "target_roles", [])),
        "interests": _has_list(getattr(profile, "domaines_interet", [])),
        "resume": _has_active_resume(profile),
    }
    total_weight = sum(weight for _name, weight in PROFILE_COMPLETION_WEIGHTS)
    earned = sum(weight for name, weight in PROFILE_COMPLETION_WEIGHTS if checks.get(name))
    missing = [name for name, _weight in PROFILE_COMPLETION_WEIGHTS if not checks.get(name)]
    return {
        "score": round((earned / total_weight) * 100) if total_weight else 0,
        "missing": missing,
    }


__all__ = ["calculate_profile_completion"]
