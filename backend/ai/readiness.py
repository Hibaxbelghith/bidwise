from __future__ import annotations

from typing import Any

from .user_features import build_user_features


CORE_SIGNAL_WEIGHTS = {
    "opportunity_types": 20,
    "target_roles": 20,
    "work_modes": 20,
}

SUPPORTING_SIGNAL_WEIGHTS = {
    "skills_or_resume": 10,
    "locations": 10,
    "employment_types": 10,
    "experience": 10,
}

STATUS_INSUFFICIENT = "INSUFFICIENT"
STATUS_PARTIAL = "PARTIAL"
STATUS_READY = "READY"


def _signal_checks(profile: Any, features: dict[str, Any]) -> dict[str, bool]:
    opportunity_types = getattr(profile, "opportunity_types", []) if profile is not None else []
    work_modes = features.get("work_modes") or features.get("remote") or []
    if isinstance(work_modes, str):
        work_modes = [work_modes] if work_modes.strip() else []

    return {
        "opportunity_types": bool(opportunity_types),
        "target_roles": bool(features.get("target_roles") or features.get("roles")),
        "work_modes": bool(work_modes),
        "skills_or_resume": bool(features.get("skills")) or bool(features.get("resume_text")),
        "locations": bool(features.get("locations") or features.get("location")),
        "employment_types": bool(features.get("employment_types")),
        "experience": bool(features.get("experience_level")) or features.get("experience_years") is not None,
    }


def calculate_recommendation_readiness(
    profile: Any,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    features = features if isinstance(features, dict) else build_user_features(profile)
    checks = _signal_checks(profile, features)

    score = 0
    for name, weight in CORE_SIGNAL_WEIGHTS.items():
        if checks.get(name):
            score += weight
    for name, weight in SUPPORTING_SIGNAL_WEIGHTS.items():
        if checks.get(name):
            score += weight

    missing_signals = [name for name, present in checks.items() if not present]
    core_ready = all(checks.get(name) for name in CORE_SIGNAL_WEIGHTS)
    if not core_ready:
        status = STATUS_INSUFFICIENT
    else:
        status = STATUS_READY

    return {
        "score": int(score),
        "status": status,
        "missing_signals": missing_signals,
        "signals": checks,
    }


def recommendation_profile_state(
    profile: Any,
    features: dict[str, Any] | None = None,
) -> str:
    readiness = calculate_recommendation_readiness(profile, features=features)
    return "complete" if readiness.get("status") == STATUS_READY else "partial"


__all__ = [
    "STATUS_INSUFFICIENT",
    "STATUS_PARTIAL",
    "STATUS_READY",
    "calculate_recommendation_readiness",
    "recommendation_profile_state",
]
