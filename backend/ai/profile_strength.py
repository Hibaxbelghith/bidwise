from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROFILE_STRENGTH_LOW_MAX = 30
PROFILE_STRENGTH_MEDIUM_MAX = 70


@dataclass(frozen=True)
class ProfileStrength:
    score: int
    level: str
    signals: dict[str, bool]

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "level": self.level,
            "signals": self.signals,
        }


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]

    cleaned = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _bool_profile_attr(profile: Any, name: str) -> bool:
    return bool(getattr(profile, name, False)) if profile is not None else False


def _level_for_score(score: int) -> str:
    if score <= PROFILE_STRENGTH_LOW_MAX:
        return "LOW"
    if score <= PROFILE_STRENGTH_MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def compute_profile_strength(profile: Any, features: dict[str, Any] | None) -> dict[str, Any]:
    """
    Compute a deterministic, lightweight recommendation readiness score.

    The score describes how much reliable semantic/business signal the profile
    carries. It does not write to the database and does not call ML services.
    """
    features = features if isinstance(features, dict) else {}

    skills = _as_list(features.get("skills"))
    roles = _as_list(features.get("target_roles")) or _as_list(features.get("roles"))
    interests = _as_list(features.get("interests"))
    locations = _as_list(features.get("locations")) or _as_list(features.get("location"))
    work_modes = _as_list(features.get("work_modes")) or _as_list(features.get("remote"))
    employment_types = _as_list(features.get("employment_types"))
    resume_text = str(features.get("resume_text") or "").strip()
    has_experience = bool(features.get("experience_level")) or features.get("experience_years") is not None
    onboarding_completed = _bool_profile_attr(profile, "onboarding_completed")

    signals = {
        "skills": bool(skills),
        "roles": bool(roles),
        "resume": bool(resume_text),
        "interests": bool(interests),
        "locations": bool(locations),
        "work_modes": bool(work_modes),
        "employment_types": bool(employment_types),
        "experience": has_experience,
        "onboarding": onboarding_completed,
    }

    score = 0
    if skills:
        score += 10 if len(skills) == 1 else 15 if len(skills) == 2 else 20
    if roles:
        score += 15 if len(roles) == 1 else 20
    if resume_text:
        score += 20
    if interests:
        score += 10
    if locations:
        score += 10
    if work_modes:
        score += 5
    if employment_types:
        score += 5
    if has_experience:
        score += 5
    if onboarding_completed:
        score += 5

    score = max(0, min(100, int(score)))
    return ProfileStrength(
        score=score,
        level=_level_for_score(score),
        signals=signals,
    ).as_dict()


def recommendation_mode_for_profile(profile_strength: dict[str, Any] | None) -> str:
    profile_strength = profile_strength if isinstance(profile_strength, dict) else {}
    if profile_strength.get("level") == "LOW":
        return "SPARSE_PROFILE"
    return "STANDARD"
