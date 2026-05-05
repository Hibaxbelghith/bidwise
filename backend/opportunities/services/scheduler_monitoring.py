import logging

from django.conf import settings
from django.core.cache import cache


logger = logging.getLogger(__name__)

DEFAULT_SCHEDULER_BEAT_INTERVAL_SECONDS = 15 * 60
SCHEDULER_DECISION_CACHE_KEY_PREFIX = "scheduler_decision"


def scheduler_decision_cache_key(source):
    return f"{SCHEDULER_DECISION_CACHE_KEY_PREFIX}:{source}"


def serialize_scheduler_decision(state):
    metrics = state.get("schedule_metrics") or {}
    score = metrics.get("adaptive_score")

    serialized_metrics = {
        "created_avg": _coerce_number(metrics.get("recent_created_avg")),
        "updated_avg": _coerce_number(metrics.get("recent_updated_avg")),
        "failure_rate": _coerce_float(metrics.get("failure_rate")),
        "zero_runs": _coerce_int(metrics.get("consecutive_zero_runs")),
    }
    if score is not None:
        serialized_metrics["score"] = _coerce_float(score)
    if metrics.get("adaptive_raw_score") is not None:
        serialized_metrics["adaptive_raw_score"] = _coerce_float(metrics.get("adaptive_raw_score"))

    decision = {
        "source": state.get("source"),
        "reason": _serialize_reason(state.get("reason")),
        "interval_seconds": _coerce_int(state.get("interval_seconds")),
        "next_run_at": _isoformat_or_none(state.get("next_run_at")),
        "metrics": serialized_metrics,
    }
    return decision


def cache_scheduler_decision_snapshot(state):
    decision = serialize_scheduler_decision(state)
    source = decision["source"]
    if not source:
        logger.warning("Scheduler decision snapshot skipped because source is missing")
        return decision

    try:
        cache.set(
            scheduler_decision_cache_key(source),
            decision,
            timeout=get_scheduler_decision_cache_timeout_seconds(),
        )
    except Exception:
        logger.exception("Could not cache scheduler decision source=%s", source)

    return decision


def get_scheduler_decision_snapshots(sources=None):
    source_keys = _get_source_keys(sources)
    return [
        normalize_scheduler_decision_snapshot(
            source,
            cache.get(scheduler_decision_cache_key(source)),
        )
        for source in source_keys
    ]


def normalize_scheduler_decision_snapshot(source, decision):
    fallback = fallback_scheduler_decision(source)
    if not isinstance(decision, dict):
        return fallback

    metrics = decision.get("metrics") if isinstance(decision.get("metrics"), dict) else {}
    return {
        "source": decision.get("source") or source,
        "reason": _serialize_reason(decision.get("reason")),
        "interval_seconds": _coerce_optional_int(decision.get("interval_seconds")),
        "next_run_at": _isoformat_or_none(decision.get("next_run_at")),
        "metrics": {
            "created_avg": _coerce_number(metrics.get("created_avg")),
            "updated_avg": _coerce_number(metrics.get("updated_avg")),
            "failure_rate": _coerce_float(metrics.get("failure_rate")),
            "zero_runs": _coerce_int(metrics.get("zero_runs")),
            **_optional_scores(metrics),
        },
    }


def fallback_scheduler_decision(source):
    return {
        "source": source,
        "reason": "NO_DATA",
        "interval_seconds": None,
        "next_run_at": None,
        "metrics": {},
    }


def get_scheduler_decision_cache_timeout_seconds():
    configured_timeout = getattr(
        settings,
        "OPPORTUNITY_SCHEDULER_DECISION_CACHE_TIMEOUT_SECONDS",
        None,
    )
    if configured_timeout is not None:
        return _coerce_positive_int(configured_timeout, 2 * DEFAULT_SCHEDULER_BEAT_INTERVAL_SECONDS)

    beat_interval = _coerce_positive_int(
        getattr(
            settings,
            "OPPORTUNITY_SCHEDULER_BEAT_INTERVAL_SECONDS",
            DEFAULT_SCHEDULER_BEAT_INTERVAL_SECONDS,
        ),
        DEFAULT_SCHEDULER_BEAT_INTERVAL_SECONDS,
    )
    return 2 * beat_interval


def _get_source_keys(sources):
    from opportunities.pipeline import get_configured_sources, sort_sources_by_priority

    if sources is None:
        return get_configured_sources()
    return sort_sources_by_priority(sources)


def _serialize_reason(reason):
    value = str(reason or "").strip()
    return value.upper() if value else "UNKNOWN"


def _coerce_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _coerce_optional_int(value):
    if value is None:
        return None
    return _coerce_int(value)


def _coerce_positive_int(value, default):
    coerced = _coerce_int(value)
    return coerced if coerced > 0 else default


def _coerce_float(value):
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _coerce_number(value):
    number = _coerce_float(value)
    return int(number) if number.is_integer() else number


def _optional_scores(metrics):
    optional_scores = {}
    if metrics.get("score") is not None:
        optional_scores["score"] = _coerce_float(metrics.get("score"))
    if metrics.get("adaptive_raw_score") is not None:
        optional_scores["adaptive_raw_score"] = _coerce_float(metrics.get("adaptive_raw_score"))
    return optional_scores


def _isoformat_or_none(value):
    return value.isoformat() if hasattr(value, "isoformat") else value or None
