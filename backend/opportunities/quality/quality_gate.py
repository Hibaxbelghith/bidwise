import re
from typing import Any

from opportunities.scraping.quality import compute_quality_score


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def _get(opportunity: Any, key: str, default: Any = None) -> Any:
    if isinstance(opportunity, dict):
        return opportunity.get(key, default)
    return getattr(opportunity, key, default)


def _set(opportunity: Any, key: str, value: Any) -> None:
    if isinstance(opportunity, dict):
        opportunity[key] = value
    else:
        setattr(opportunity, key, value)


def build_ml_text(opportunity: Any) -> str:
    parts = [
        _as_text(_get(opportunity, "titre") or _get(opportunity, "title")),
        _as_text(_get(opportunity, "organisation_nom") or _get(opportunity, "organization")),
        _as_text(_get(opportunity, "organization_normalized")),
        _as_text(_get(opportunity, "ville") or _get(opportunity, "location")),
        _as_text(_get(opportunity, "description")),
        _as_text(_get(opportunity, "type_opportunite") or _get(opportunity, "type")),
    ]
    return _as_text(" ".join(part for part in parts if part))


def get_quality_tier(opportunity: Any) -> str:
    quality_score = float(_get(opportunity, "quality_score", 0.0) or 0.0)
    if quality_score >= 0.75:
        return "HIGH"
    if quality_score >= 0.50:
        return "MEDIUM"
    return "LOW"


def evaluate_opportunity(opportunity: Any) -> Any:
    title = _as_text(_get(opportunity, "titre") or _get(opportunity, "title"))
    description = _as_text(_get(opportunity, "description"))
    source_item_url = _as_text(_get(opportunity, "source_item_url") or _get(opportunity, "url"))

    # Early filter: keep this gate lightweight and deterministic.
    unusable_reason = ""
    if not title:
        unusable_reason = "missing_title"
    elif not description:
        unusable_reason = "missing_description"
    elif not source_item_url:
        unusable_reason = "missing_source_item_url"
    elif len(description) < 30:
        unusable_reason = "description_too_short"

    is_usable = not bool(unusable_reason)

    quality_score = compute_quality_score(
        organisation_nom=_as_text(_get(opportunity, "organisation_nom") or _get(opportunity, "organization")),
        ville=_as_text(_get(opportunity, "ville") or _get(opportunity, "location")),
        description=description,
        source_item_url=source_item_url,
        date_confidence=_as_text(_get(opportunity, "date_confidence") or "FALLBACK"),
    )

    _set(opportunity, "quality_score", float(quality_score))
    _set(opportunity, "quality_tier", get_quality_tier(opportunity))
    _set(opportunity, "ml_text", build_ml_text(opportunity))
    _set(opportunity, "ready_for_recommendation", bool((float(quality_score) * 5.0) >= 4.0))
    _set(opportunity, "is_usable", bool(is_usable))
    _set(opportunity, "unusable_reason", unusable_reason)

    return opportunity
