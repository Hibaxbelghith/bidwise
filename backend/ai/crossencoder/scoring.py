from __future__ import annotations

import concurrent.futures
import logging
import math
import time
from typing import Any

from ai.recommendation_service import _clean_list, _get_value

from .loader import get_cross_encoder_config, get_cross_encoder_model, mark_cross_encoder_unavailable
from .models import CrossEncoderCandidateScore, CrossEncoderTimeout, CrossEncoderUnavailable


logger = logging.getLogger(__name__)


def score_opportunities(
    features: dict[str, Any] | None,
    opportunities: list[Any],
) -> list[CrossEncoderCandidateScore]:
    opportunities = list(opportunities)
    if not opportunities:
        return []

    profile_text = build_profile_text(features or {})
    if not profile_text.strip():
        raise CrossEncoderUnavailable("CrossEncoder profile text is empty")

    pairs = [
        (profile_text, build_opportunity_text(opportunity))
        for opportunity in opportunities
    ]
    raw_scores, elapsed_ms = _predict_pairs(pairs)
    normalized = [_normalize_score(score) for score in raw_scores]
    config = get_cross_encoder_config()
    return [
        CrossEncoderCandidateScore(
            score=score,
            raw_score=_safe_float(raw_score),
            metadata={
                "model": config.model_name,
                "elapsed_ms": round(elapsed_ms, 3),
                "pair_index": index,
            },
        )
        for index, (score, raw_score) in enumerate(zip(normalized, raw_scores))
    ]


def build_profile_text(features: dict[str, Any]) -> str:
    config = get_cross_encoder_config()
    lines = [
        "PROFILE:",
        _line("Structured profile summary", _profile_summary(features)),
        _line("Semantic CV summary", features.get("resume_text")),
        _line("Skills", _joined(features.get("skills"))),
        _line("Roles", _joined(features.get("target_roles") or features.get("roles"))),
        _line("Domains", _joined(features.get("interests") or features.get("semantic_resume_domains"))),
        _line("Experience", _experience_text(features)),
    ]
    return _truncate("\n".join(line for line in lines if line), config.max_text_chars)


def build_opportunity_text(opportunity: Any) -> str:
    config = get_cross_encoder_config()
    lines = [
        "JOB:",
        _line("Title", _get_value(opportunity, "titre", "") or _get_value(opportunity, "title", "")),
        _line("Description", _get_value(opportunity, "description", "")),
        _line("Skills", _joined(_get_value(opportunity, "skills", []))),
        _line("Company", _get_value(opportunity, "organisation_nom", "") or _get_value(opportunity, "company", "")),
        _line("Location", _get_value(opportunity, "ville", "") or _get_value(opportunity, "location", "")),
    ]
    return _truncate("\n".join(line for line in lines if line), config.max_text_chars)


def _predict_pairs(pairs: list[tuple[str, str]]) -> tuple[list[float], float]:
    config = get_cross_encoder_config()
    started = time.perf_counter()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="crossencoder")
    future = executor.submit(_predict_pairs_sync, pairs, config.batch_size)
    try:
        raw_scores = future.result(timeout=config.timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        mark_cross_encoder_unavailable(
            f"CrossEncoder scoring exceeded {config.timeout_seconds:.2f}s timeout"
        )
        raise CrossEncoderTimeout("CrossEncoder scoring timed out") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return _flatten_scores(raw_scores), elapsed_ms


def _predict_pairs_sync(pairs: list[tuple[str, str]], batch_size: int) -> Any:
    model = get_cross_encoder_model()
    return model.predict(
        pairs,
        batch_size=batch_size,
        show_progress_bar=False,
    )


def _flatten_scores(raw_scores: Any) -> list[float]:
    values = raw_scores
    if hasattr(values, "tolist"):
        values = values.tolist()
    if not isinstance(values, list):
        values = list(values)

    flattened = []
    for item in values:
        if hasattr(item, "tolist"):
            item = item.tolist()
        if isinstance(item, (list, tuple)):
            item = item[-1] if item else 0.0
        flattened.append(_safe_float(item))
    return flattened


def _normalize_score(value: Any) -> float:
    raw = _safe_float(value)
    if 0.0 <= raw <= 1.0:
        return raw
    if raw >= 20.0:
        return 1.0
    if raw <= -20.0:
        return 0.0
    return max(0.0, min(1.0, 1.0 / (1.0 + math.exp(-raw))))


def _safe_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if math.isfinite(parsed) else 0.0


def _line(label: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return f"{label}: {text}"


def _joined(value: Any) -> str:
    return ", ".join(_clean_list(value))


def _experience_text(features: dict[str, Any]) -> str:
    parts = []
    if features.get("experience_level"):
        parts.append(str(features["experience_level"]))
    if features.get("experience_years") not in (None, ""):
        parts.append(f"{features['experience_years']} years")
    return ", ".join(parts)


def _profile_summary(features: dict[str, Any]) -> str:
    pieces = []
    if features.get("roles") or features.get("target_roles"):
        pieces.append(f"roles={_joined(features.get('target_roles') or features.get('roles'))}")
    if features.get("skills"):
        pieces.append(f"skills={_joined(features.get('skills'))}")
    if features.get("interests"):
        pieces.append(f"domains={_joined(features.get('interests'))}")
    if features.get("location"):
        pieces.append(f"location={features.get('location')}")
    return "; ".join(piece for piece in pieces if piece)


def _truncate(value: str, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].strip()
