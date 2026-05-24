from __future__ import annotations

import logging
import math
import threading
import time
from functools import lru_cache
from typing import Any

from django.conf import settings
from django.utils import timezone

from ai.embeddings import build_user_embedding_text, build_user_features_hash
from opportunities.nlp.nlp_preprocessing import prepare_combined_text


logger = logging.getLogger(__name__)

DEFAULT_JOBBERT_MODEL = "TechWolf/JobBERT-v3"
_RERANK_LOCK = threading.Lock()


def jobbert_enabled() -> bool:
    return bool(getattr(settings, "JOBBERT_RERANK_ENABLED", False))


def jobbert_model_name() -> str:
    return str(getattr(settings, "JOBBERT_MODEL", DEFAULT_JOBBERT_MODEL) or DEFAULT_JOBBERT_MODEL).strip()


def _setting_float(name: str, default: float) -> float:
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _setting_int(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("sentence-transformers is required for JobBERT reranking.") from exc

    logger.info("Loading JobBERT model '%s' on CPU", model_name)
    return SentenceTransformer(model_name, device="cpu")


def _clean_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _dot(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    score = 0.0
    for left_value, right_value in zip(left, right):
        try:
            score += float(left_value) * float(right_value)
        except (TypeError, ValueError):
            return 0.0
    return score if math.isfinite(score) else 0.0


def generate_jobbert_embeddings_batch(texts: list[str], *, model_name: str | None = None, batch_size: int | None = None):
    cleaned = [
        _clean_text(text, max_chars=max(500, _setting_int("JOBBERT_MAX_TEXT_CHARS", 2200)))
        for text in texts
    ]
    if not cleaned:
        return []
    model = _load_model(model_name or jobbert_model_name())
    vectors = model.encode(
        cleaned,
        batch_size=batch_size or max(1, _setting_int("JOBBERT_BATCH_SIZE", 16)),
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [[float(item) for item in vector.tolist()] for vector in vectors]


def get_or_build_profile_jobbert_embedding(profile, features: dict[str, Any]) -> list[float]:
    if profile is None or not isinstance(features, dict):
        return []
    content_hash = build_user_features_hash(features)
    model_name = jobbert_model_name()
    existing = getattr(profile, "jobbert_embedding", None)
    if (
        isinstance(existing, list)
        and existing
        and getattr(profile, "jobbert_embedding_model", "") == model_name
        and getattr(profile, "jobbert_embedding_content_hash", "") == content_hash
    ):
        return [float(item) for item in existing]

    text = _clean_text(
        build_user_embedding_text(features),
        max_chars=max(500, _setting_int("JOBBERT_MAX_TEXT_CHARS", 2200)),
    )
    if not text:
        return []
    vector = generate_jobbert_embeddings_batch([text], model_name=model_name, batch_size=1)[0]
    profile.jobbert_embedding = vector
    profile.jobbert_embedding_model = model_name
    profile.jobbert_embedding_content_hash = content_hash
    profile.jobbert_embedding_updated_at = timezone.now()
    profile.save(
        update_fields=[
            "jobbert_embedding",
            "jobbert_embedding_model",
            "jobbert_embedding_content_hash",
            "jobbert_embedding_updated_at",
        ]
    )
    return vector


def build_precomputed_jobbert_scores(profile_vector: list[float], opportunities: list[Any]) -> dict[int, float]:
    if not profile_vector or not opportunities:
        return {}
    model_name = jobbert_model_name()
    scores: dict[int, float] = {}
    for opportunity in opportunities:
        opportunity_id = getattr(opportunity, "pk", None) or getattr(opportunity, "id", None)
        if opportunity_id is None and isinstance(opportunity, dict):
            opportunity_id = opportunity.get("id")
        if not opportunity_id:
            continue
        if getattr(opportunity, "jobbert_embedding_model", "") != model_name:
            continue
        vector = getattr(opportunity, "jobbert_embedding_vector", None)
        if isinstance(opportunity, dict):
            vector = opportunity.get("jobbert_embedding_vector")
        if not isinstance(vector, list) or not vector:
            continue
        scores[int(opportunity_id)] = round(max(0.0, min(1.0, _dot(profile_vector, vector))), 4)
    return scores


def build_jobbert_scores(features: dict[str, Any], opportunities: list[Any]) -> dict[int, float]:
    if not jobbert_enabled() or not features or not opportunities:
        return {}

    max_candidates = max(1, _setting_int("JOBBERT_MAX_CANDIDATES", 20))
    max_text_chars = max(500, _setting_int("JOBBERT_MAX_TEXT_CHARS", 2200))
    batch_size = max(1, _setting_int("JOBBERT_BATCH_SIZE", 16))
    timeout_seconds = max(1.0, _setting_float("JOBBERT_TIMEOUT_SECONDS", 12.0))
    model_name = str(getattr(settings, "JOBBERT_MODEL", DEFAULT_JOBBERT_MODEL) or DEFAULT_JOBBERT_MODEL).strip()

    selected = list(opportunities[:max_candidates])
    profile_text = _clean_text(build_user_embedding_text(features), max_chars=max_text_chars)
    if not profile_text:
        return {}

    candidate_ids: list[int] = []
    candidate_texts: list[str] = []
    for opportunity in selected:
        opportunity_id = getattr(opportunity, "pk", None) or getattr(opportunity, "id", None)
        if opportunity_id is None and isinstance(opportunity, dict):
            opportunity_id = opportunity.get("id")
        text = _clean_text(prepare_combined_text(opportunity), max_chars=max_text_chars)
        if not opportunity_id or not text:
            continue
        candidate_ids.append(int(opportunity_id))
        candidate_texts.append(text)

    if not candidate_texts:
        return {}

    if not _RERANK_LOCK.acquire(blocking=False):
        logger.info("JobBERT reranking skipped because another request is already using the model")
        return {}
    try:
        started_at = time.monotonic()
        try:
            model = _load_model(model_name)
            vectors = model.encode(
                [profile_text, *candidate_texts],
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        except Exception:
            logger.exception("JobBERT reranking failed; continuing without JobBERT scores")
            return {}

        elapsed = time.monotonic() - started_at
        if elapsed > timeout_seconds:
            logger.warning(
                "JobBERT reranking exceeded soft timeout elapsed=%.2fs timeout=%.2fs candidates=%s",
                elapsed,
                timeout_seconds,
                len(candidate_texts),
            )
            return {}
    finally:
        _RERANK_LOCK.release()

    profile_vector = vectors[0].tolist()
    scores: dict[int, float] = {}
    for opportunity_id, vector in zip(candidate_ids, vectors[1:]):
        scores[opportunity_id] = round(
            max(0.0, min(1.0, _dot(profile_vector, vector.tolist()))),
            4,
        )
    return scores


def jobbert_adjustment(score: float) -> float:
    high_threshold = _setting_float("JOBBERT_HIGH_THRESHOLD", 0.65)
    medium_threshold = _setting_float("JOBBERT_MEDIUM_THRESHOLD", 0.55)
    weak_threshold = _setting_float("JOBBERT_WEAK_THRESHOLD", 0.45)
    high_bonus = _setting_float("JOBBERT_HIGH_BONUS", 0.08)
    medium_bonus = _setting_float("JOBBERT_MEDIUM_BONUS", 0.04)
    weak_penalty = _setting_float("JOBBERT_WEAK_PENALTY", 0.04)

    value = float(score or 0.0)
    if value >= high_threshold:
        return high_bonus
    if value >= medium_threshold:
        return medium_bonus
    if value < weak_threshold:
        return -weak_penalty
    return 0.0
