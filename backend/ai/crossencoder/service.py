from __future__ import annotations

import logging
from typing import Any

from ai.recommendation_service import _clamp_score, _get_value, _sort_key, _update_score

from .loader import get_cross_encoder_config, is_cross_encoder_enabled
from .models import CrossEncoderUnavailable
from .scoring import score_opportunities


logger = logging.getLogger(__name__)


def rerank_ranked_opportunities(
    ranked: list[Any],
    *,
    features: dict[str, Any] | None = None,
) -> list[Any]:
    """
    Apply CrossEncoder reranking to a bounded top-candidate shortlist.

    This function is intentionally additive. It never retrieves candidates,
    never changes the API shape, and returns the original ranking unchanged if
    CrossEncoder scoring is disabled, unavailable, slow, or invalid.
    """
    ranked = list(ranked or [])
    if not ranked:
        return ranked

    config = get_cross_encoder_config()
    if not is_cross_encoder_enabled() or config.weight <= 0.0:
        return ranked
    if not _has_profile_signal(features or {}):
        return ranked

    shortlist_size = min(len(ranked), config.max_candidates)
    shortlist = ranked[:shortlist_size]
    tail = ranked[shortlist_size:]

    try:
        cross_scores = score_opportunities(features or {}, shortlist)
    except CrossEncoderUnavailable as exc:
        logger.warning("CrossEncoder rerank unavailable; preserving existing ranking reason=%s", exc)
        return ranked
    except Exception:
        logger.warning("CrossEncoder rerank failed; preserving existing ranking", exc_info=True)
        return ranked

    if len(cross_scores) != len(shortlist):
        logger.warning(
            "CrossEncoder rerank returned unexpected score count expected=%s actual=%s; preserving existing ranking",
            len(shortlist),
            len(cross_scores),
        )
        return ranked

    for item, cross_score in zip(shortlist, cross_scores):
        existing_score = _safe_score(_get_value(item, "match_score", _get_value(item, "score", 0.0)))
        blended = blend_scores(existing_score, cross_score.score, config.weight)
        blended = max(blended, _structured_evidence_floor(item))
        _set_crossencoder_metadata(
            item,
            cross_score=cross_score.score,
            raw_score=cross_score.raw_score,
            weight=config.weight,
            metadata=cross_score.metadata,
        )
        _update_score(item, blended)

    combined = list(shortlist) + list(tail)
    combined.sort(key=_sort_key, reverse=True)
    return combined


def blend_scores(existing_score: float, crossencoder_score: float, weight: float) -> float:
    weight = _clamp_score(weight)
    return _clamp_score((existing_score * (1.0 - weight)) + (_clamp_score(crossencoder_score) * weight))


def _has_profile_signal(features: dict[str, Any]) -> bool:
    for key in (
        "skills",
        "profile_skills",
        "semantic_resume_skills",
        "semantic_resume_tools",
        "semantic_resume_domains",
        "roles",
        "target_roles",
        "interests",
        "resume_text",
    ):
        value = features.get(key)
        if isinstance(value, (list, tuple, set)) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def _structured_evidence_floor(item: Any) -> float:
    debug = _get_value(item, "recommendation_debug", {})
    if not isinstance(debug, dict):
        return 0.0
    return _safe_score(debug.get("structured_evidence_score_floor"))


def _set_crossencoder_metadata(
    item: Any,
    *,
    cross_score: float,
    raw_score: float,
    weight: float,
    metadata: dict[str, Any],
) -> None:
    payload = dict(metadata or {})
    if isinstance(item, dict):
        item["crossencoder_score"] = _clamp_score(cross_score)
        item["crossencoder_raw_score"] = raw_score
        item["crossencoder_weight"] = weight
        item["crossencoder_metadata"] = payload
        return

    setattr(item, "crossencoder_score", _clamp_score(cross_score))
    setattr(item, "crossencoder_raw_score", raw_score)
    setattr(item, "crossencoder_weight", weight)
    setattr(item, "crossencoder_metadata", payload)


def _safe_score(value: Any) -> float:
    try:
        return _clamp_score(float(value or 0.0))
    except (TypeError, ValueError):
        return 0.0
