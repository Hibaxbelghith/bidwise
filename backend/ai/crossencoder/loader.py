from __future__ import annotations

import inspect
import logging
import threading
import time
from pathlib import Path
from typing import Any

from django.conf import settings

from .models import CrossEncoderConfig, CrossEncoderUnavailable


logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_MODEL: Any | None = None
_MODEL_NAME = ""
_UNAVAILABLE_UNTIL = 0.0
_UNAVAILABLE_REASON = ""
_LOCK = threading.Lock()


def get_cross_encoder_config() -> CrossEncoderConfig:
    return CrossEncoderConfig(
        enabled=bool(getattr(settings, "CROSS_ENCODER_ENABLED", True)),
        model_name=str(getattr(settings, "CROSS_ENCODER_MODEL", DEFAULT_MODEL_NAME) or DEFAULT_MODEL_NAME),
        max_candidates=_bounded_int(getattr(settings, "CROSS_ENCODER_MAX_CANDIDATES", 30), 1, 100),
        weight=_bounded_float(getattr(settings, "CROSS_ENCODER_WEIGHT", 0.25), 0.0, 1.0),
        batch_size=_bounded_int(getattr(settings, "CROSS_ENCODER_BATCH_SIZE", 8), 1, 32),
        timeout_seconds=_bounded_float(getattr(settings, "CROSS_ENCODER_TIMEOUT_SECONDS", 2.0), 0.1, 30.0),
        max_text_chars=_bounded_int(getattr(settings, "CROSS_ENCODER_MAX_TEXT_CHARS", 2400), 200, 12000),
        reason_threshold=_bounded_float(getattr(settings, "CROSS_ENCODER_REASON_THRESHOLD", 0.82), 0.0, 1.0),
        local_files_only=bool(getattr(settings, "CROSS_ENCODER_LOCAL_FILES_ONLY", True)),
    )


def is_cross_encoder_enabled() -> bool:
    return get_cross_encoder_config().enabled


def get_cross_encoder_model() -> Any:
    global _MODEL, _MODEL_NAME

    config = get_cross_encoder_config()
    if not config.enabled:
        raise CrossEncoderUnavailable("CrossEncoder reranking is disabled")

    now = time.monotonic()
    if _UNAVAILABLE_UNTIL > now:
        raise CrossEncoderUnavailable(_UNAVAILABLE_REASON or "CrossEncoder is temporarily unavailable")

    if _MODEL is not None and _MODEL_NAME == config.model_name:
        return _MODEL

    with _LOCK:
        now = time.monotonic()
        if _UNAVAILABLE_UNTIL > now:
            raise CrossEncoderUnavailable(_UNAVAILABLE_REASON or "CrossEncoder is temporarily unavailable")
        if _MODEL is not None and _MODEL_NAME == config.model_name:
            return _MODEL

        if config.local_files_only and not _local_model_available(config.model_name):
            _mark_unavailable(f"CrossEncoder model is not present in local HuggingFace cache: {config.model_name}")
            raise CrossEncoderUnavailable("CrossEncoder model is unavailable locally")

        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:
            _mark_unavailable(f"sentence-transformers CrossEncoder import failed: {exc}")
            raise CrossEncoderUnavailable("CrossEncoder dependency is unavailable") from exc

        kwargs: dict[str, Any] = {
            "device": "cpu",
            "max_length": 384,
        }
        if config.local_files_only:
            kwargs.update(_local_files_only_kwargs(CrossEncoder))

        try:
            model = CrossEncoder(config.model_name, **kwargs)
        except Exception as exc:
            _mark_unavailable(f"CrossEncoder model load failed: {exc}")
            raise CrossEncoderUnavailable("CrossEncoder model is unavailable") from exc

        _MODEL = model
        _MODEL_NAME = config.model_name
        logger.info("CrossEncoder model loaded model=%s device=cpu", config.model_name)
        return _MODEL


def mark_cross_encoder_unavailable(reason: str) -> None:
    _mark_unavailable(reason)


def get_cross_encoder_status() -> dict[str, Any]:
    config = get_cross_encoder_config()
    unavailable_for = max(0.0, _UNAVAILABLE_UNTIL - time.monotonic())
    return {
        "enabled": config.enabled,
        "model_name": config.model_name,
        "loaded": _MODEL is not None and _MODEL_NAME == config.model_name,
        "local_files_only": config.local_files_only,
        "unavailable_for_seconds": round(unavailable_for, 3),
        "unavailable_reason": _UNAVAILABLE_REASON,
    }


def reset_cross_encoder_cache() -> None:
    global _MODEL, _MODEL_NAME, _UNAVAILABLE_UNTIL, _UNAVAILABLE_REASON
    with _LOCK:
        _MODEL = None
        _MODEL_NAME = ""
        _UNAVAILABLE_UNTIL = 0.0
        _UNAVAILABLE_REASON = ""


def _mark_unavailable(reason: str) -> None:
    global _MODEL, _MODEL_NAME, _UNAVAILABLE_UNTIL, _UNAVAILABLE_REASON
    ttl = _bounded_int(getattr(settings, "CROSS_ENCODER_UNAVAILABLE_TTL_SECONDS", 300), 1, 3600)
    _MODEL = None
    _MODEL_NAME = ""
    _UNAVAILABLE_UNTIL = time.monotonic() + ttl
    _UNAVAILABLE_REASON = str(reason or "CrossEncoder unavailable")
    logger.warning("CrossEncoder unavailable; skipping rerank reason=%s", _UNAVAILABLE_REASON)


def _local_files_only_kwargs(cross_encoder_cls: Any) -> dict[str, Any]:
    try:
        signature = inspect.signature(cross_encoder_cls)
    except (TypeError, ValueError):
        signature = None

    if signature is not None and "local_files_only" in signature.parameters:
        return {"local_files_only": True}

    return {
        "automodel_args": {"local_files_only": True},
        "tokenizer_args": {"local_files_only": True},
        "config_args": {"local_files_only": True},
    }


def _local_model_available(model_name: str) -> bool:
    model_path = Path(model_name)
    if model_path.exists():
        return True
    try:
        from huggingface_hub import try_to_load_from_cache
    except Exception:
        return True
    try:
        return try_to_load_from_cache(model_name, "config.json") is not None
    except Exception:
        return False


def _bounded_int(value: Any, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))


def _bounded_float(value: Any, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(maximum, parsed))
