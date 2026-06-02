"""
Scheduler/orchestrator for opportunity source collection.

This module decides which scraping sources should run, when they should run,
how stale or failed runs are handled, and how collection results are recorded.
It is not the business data pipeline for transforming one raw opportunity into
a normalized, enriched, scored, and materialized opportunity.
"""

import inspect
import logging
from datetime import timedelta

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from opportunities.models import PipelineRun, PipelineRunStatus, SourceSchedulerState
from opportunities.services.scheduler_monitoring import cache_scheduler_decision_snapshot
from opportunities.scraping.pipeline import run_collection
from opportunities.scraping.sources import (
    EmploiTunisieScraper,
    KeejobScraper,
    LinkedInScraper,
    MarchesPublicsScraper,
)


logger = logging.getLogger(__name__)
DEFAULT_ADAPTIVE_RECENT_RUN_LIMIT = 5
DEFAULT_ADAPTIVE_ZERO_RUNS_THRESHOLD = 3
DEFAULT_ADAPTIVE_FAILURE_THRESHOLD = 2
DEFAULT_ADAPTIVE_HIGH_CREATED_AVG = 5
DEFAULT_ADAPTIVE_HIGH_UPDATED_AVG = 10
DEFAULT_ADAPTIVE_EMA_ALPHA = 0.5
DEFAULT_ADAPTIVE_SCORE_SPEEDUP_THRESHOLD = 0.75
DEFAULT_ADAPTIVE_SCORE_COOLDOWN_THRESHOLD = -0.35
DEFAULT_ADAPTIVE_HARD_FAILURE_RATE_THRESHOLD = 0.5
MAX_ADAPTIVE_SCORE = 1.0
MIN_ADAPTIVE_INTERVAL_SECONDS = 5 * 60
MAX_ADAPTIVE_INTERVAL_SECONDS = 12 * 60 * 60
ADAPTIVE_CREATED_SPEEDUP_DIVISOR = 2
ADAPTIVE_UPDATED_SPEEDUP_NUMERATOR = 3
ADAPTIVE_UPDATED_SPEEDUP_DENOMINATOR = 4
ADAPTIVE_FAILURE_BACKOFF_NUMERATOR = 3
ADAPTIVE_FAILURE_BACKOFF_DENOMINATOR = 2
ADAPTIVE_SCORE_SPEEDUP_NUMERATOR = 3
ADAPTIVE_SCORE_SPEEDUP_DENOMINATOR = 4
ADAPTIVE_SCORE_COOLDOWN_NUMERATOR = 3
ADAPTIVE_SCORE_COOLDOWN_DENOMINATOR = 2
MAX_ZERO_RUN_SLOWDOWN_MULTIPLIER = 3

SCRAPER_REGISTRY = {
    "keejob": KeejobScraper,
    "linkedin": LinkedInScraper,
    "emploi_tn": EmploiTunisieScraper,
    "marches_publics": MarchesPublicsScraper,
}

SOURCE_ALIASES = {
    "emploitunisie": "emploi_tn",
    "marchespublics": "marches_publics",
}

DEFAULT_SOURCE_CONFIG = {
    "linkedin": {
        "priority": 1,
        "schedule_seconds": 60 * 60,
        "stale_schedule_seconds": 15 * 60,
        "failure_retry_seconds": 15 * 60,
        "stale_after_seconds": 12 * 60 * 60,
        "max_duration_seconds": 10 * 60,
    },
    "keejob": {
        "priority": 2,
        "schedule_seconds": 2 * 60 * 60,
        "stale_schedule_seconds": 30 * 60,
        "failure_retry_seconds": 30 * 60,
        "stale_after_seconds": 12 * 60 * 60,
        "max_duration_seconds": 20 * 60,
    },
    "emploi_tn": {
        "priority": 3,
        "schedule_seconds": 6 * 60 * 60,
        "stale_schedule_seconds": 60 * 60,
        "failure_retry_seconds": 60 * 60,
        "stale_after_seconds": 24 * 60 * 60,
        "max_duration_seconds": 20 * 60,
    },
    "marches_publics": {
        "priority": 4,
        "schedule_seconds": 12 * 60 * 60,
        "stale_schedule_seconds": 2 * 60 * 60,
        "failure_retry_seconds": 2 * 60 * 60,
        "stale_after_seconds": 48 * 60 * 60,
        "max_duration_seconds": 30 * 60,
    },
}


def _coerce_positive_int(value, default):
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced > 0 else default


def _coerce_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_ratio(value, default):
    coerced = _coerce_float(value, default)
    if coerced <= 0:
        return default
    return min(coerced, 1.0)


def _isoformat_or_none(value):
    return value.isoformat() if value else None


def _clamp_interval_seconds(value, *, min_seconds=MIN_ADAPTIVE_INTERVAL_SECONDS, max_seconds=MAX_ADAPTIVE_INTERVAL_SECONDS):
    return max(min_seconds, min(int(value), max_seconds))


def _settings_source_config():
    config = getattr(settings, "OPPORTUNITY_SOURCE_CONFIG", None)
    if config is None:
        config = getattr(settings, "SOURCE_CONFIG", {})
    return config if isinstance(config, dict) else {}


def _source_scraper_config(source_key):
    config = getattr(settings, "SCRAPER_CONFIG", {})
    source_config = config.get(source_key, {}) if isinstance(config, dict) else {}
    return source_config if isinstance(source_config, dict) else {}


def normalize_source(source):
    source_key = (source or get_default_source()).lower().strip()
    return SOURCE_ALIASES.get(source_key, source_key)


def _normalize_source_list(sources):
    normalized_sources = []
    seen = set()
    for source in sources:
        source_key = normalize_source(source)
        if source_key not in seen:
            normalized_sources.append(source_key)
            seen.add(source_key)
    return normalized_sources


def get_source_config(source):
    source_key = normalize_source(source)
    config = dict(DEFAULT_SOURCE_CONFIG.get(source_key, {}))
    settings_config = _settings_source_config()
    configured = settings_config.get(source_key, {})
    if isinstance(configured, dict):
        config.update(configured)
    return config


def get_source_priority(source):
    return _coerce_positive_int(get_source_config(source).get("priority"), 999)


def sort_sources_by_priority(sources):
    if isinstance(sources, str):
        sources = [sources]
    return sorted(_normalize_source_list(sources), key=lambda source: (get_source_priority(source), source))


def get_configured_sources(*, ordered=True):
    configured = getattr(settings, "OPPORTUNITY_PIPELINE_SOURCES", ["keejob"])
    sources = _normalize_source_list(configured)
    return sort_sources_by_priority(sources) if ordered else sources


def get_default_source():
    sources = get_configured_sources(ordered=True)
    return sources[0] if sources else "keejob"


def _valid_source_keys():
    return sorted(set(SCRAPER_REGISTRY) | set(SOURCE_ALIASES))


def _build_scraper_kwargs(source_key, scraper_cls, options):
    source_config = _source_scraper_config(source_key)
    delay = source_config.get("delay", ())
    try:
        default_min_delay, default_max_delay = delay
    except (TypeError, ValueError):
        default_min_delay, default_max_delay = None, None

    requested_kwargs = {
        "max_pages": options.get("max_pages") or source_config.get("max_pages"),
        "keyword": options.get("keyword"),
        "location": options.get("location"),
        "max_records": options.get("max_records"),
        "timeout": options.get("timeout"),
        "min_delay": options.get("min_delay") if options.get("min_delay") is not None else default_min_delay,
        "max_delay": options.get("max_delay") if options.get("max_delay") is not None else default_max_delay,
        "stage_only": options.get("stage_only"),
        "fetch_details": (
            options.get("fetch_details")
            if options.get("fetch_details") is not None
            else source_config.get("fetch_details")
        ),
    }
    init_signature = inspect.signature(scraper_cls.__init__)
    return {
        key: value
        for key, value in requested_kwargs.items()
        if value is not None and key in init_signature.parameters
    }


def resolve_source_collection(source, **options):
    source_key = normalize_source(source)
    scraper_cls = SCRAPER_REGISTRY.get(source_key)

    if not scraper_cls:
        valid = ", ".join(_valid_source_keys())
        raise CommandError(f"Unknown source '{source_key}'. Available: {valid}")

    return {
        "source": source_key,
        "priority": get_source_priority(source_key),
        "scraper_cls": scraper_cls,
        "scraper_kwargs": _build_scraper_kwargs(source_key, scraper_cls, options),
    }


def run_source_collection(source, **options):
    collection = resolve_source_collection(source, **options)
    scraper = collection["scraper_cls"](**collection["scraper_kwargs"])
    collection["stats"] = run_collection(scraper=scraper)
    return collection


def _finished_at(run):
    if run is None:
        return None
    return run.finished_at or run.started_at


def _get_max_duration_seconds(source_key):
    config = get_source_config(source_key)
    default = DEFAULT_SOURCE_CONFIG.get(source_key, {}).get("max_duration_seconds", 30 * 60)
    return _coerce_positive_int(config.get("max_duration_seconds"), default)


def _running_age_seconds(run, *, now_value):
    if run is None or run.status != PipelineRunStatus.RUNNING:
        return 0.0
    return max((now_value - run.started_at).total_seconds(), 0.0)


def _run_total(run, total_field, legacy_field):
    value = getattr(run, total_field, 0) or 0
    if value:
        return int(value)
    return int(getattr(run, legacy_field, 0) or 0)


def _average(values):
    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)


def _ema_next(new_value, old_value, *, alpha):
    new_value = float(new_value or 0.0)
    if old_value is None:
        return new_value
    return (alpha * new_value) + ((1 - alpha) * old_value)


def _ema(values, *, alpha):
    current = None
    for value in values:
        current = _ema_next(value, current, alpha=alpha)
    return current if current is not None else 0.0


def _normalize_adaptive_score(score):
    bounded_score = max(0.0, min(float(score or 0.0), MAX_ADAPTIVE_SCORE))
    return bounded_score / MAX_ADAPTIVE_SCORE


def _latest_activity_run(source):
    return (
        PipelineRun.objects.filter(source=source, status=PipelineRunStatus.SUCCESS)
        .filter(
            Q(total_created__gt=0)
            | Q(created_count__gt=0)
            | Q(total_updated__gt=0)
            | Q(updated_count__gt=0)
        )
        .order_by("-started_at", "-id")
        .first()
    )


def get_source_schedule_metrics(source, *, recent_run_limit=None):
    source_key = normalize_source(source)
    config = get_source_config(source_key)
    ema_alpha = _coerce_ratio(
        config.get("adaptive_ema_alpha"),
        DEFAULT_ADAPTIVE_EMA_ALPHA,
    )
    recent_run_limit = _coerce_positive_int(
        recent_run_limit or config.get("adaptive_recent_run_limit"),
        DEFAULT_ADAPTIVE_RECENT_RUN_LIMIT,
    )
    recent_runs = list(
        PipelineRun.objects.filter(source=source_key)
        .exclude(status=PipelineRunStatus.RUNNING)
        .order_by("-started_at", "-id")[:recent_run_limit]
    )
    successful_runs = [
        run
        for run in recent_runs
        if run.status == PipelineRunStatus.SUCCESS
    ]
    created_values = [
        _run_total(run, "total_created", "created_count")
        for run in reversed(successful_runs)
    ]
    updated_values = [
        _run_total(run, "total_updated", "updated_count")
        for run in reversed(successful_runs)
    ]
    failure_values = [
        1.0 if run.status == PipelineRunStatus.FAILED else 0.0
        for run in reversed(recent_runs)
    ]

    consecutive_zero_runs = 0
    for run in successful_runs:
        if _run_total(run, "total_created", "created_count") > 0:
            break
        consecutive_zero_runs += 1

    failure_count_recent = sum(
        1 for run in recent_runs if run.status == PipelineRunStatus.FAILED
    )
    failed_pages_recent = sum(
        _run_total(run, "total_failed_pages", "total_failed_pages")
        for run in recent_runs
    )

    return {
        "recent_run_count": len(recent_runs),
        "recent_success_count": len(successful_runs),
        "recent_created_avg": _ema(created_values, alpha=ema_alpha),
        "recent_updated_avg": _ema(updated_values, alpha=ema_alpha),
        "recent_created_mean": _average(created_values),
        "recent_updated_mean": _average(updated_values),
        "created_per_run": _average(created_values),
        "trend": created_values,
        "ema_alpha": ema_alpha,
        "consecutive_zero_runs": consecutive_zero_runs,
        "failure_count_recent": failure_count_recent,
        "failure_rate": _ema(failure_values, alpha=ema_alpha),
        "failure_rate_mean": failure_count_recent / len(recent_runs) if recent_runs else 0.0,
        "failed_pages_recent": failed_pages_recent,
    }


def _build_adaptive_score(metrics, state, *, high_created_threshold, high_updated_threshold, failure_threshold):
    created_signal = float(metrics.get("recent_created_avg", 0.0) or 0.0)
    updated_signal = float(metrics.get("recent_updated_avg", 0.0) or 0.0)
    failure_rate = float(metrics.get("failure_rate", 0.0) or 0.0)
    failure_count_recent = int(metrics.get("failure_count_recent", 0) or 0)

    freshness_score = 1.0 if state.get("is_stale") else 0.0
    volume_score = min(
        1.0,
        (created_signal / max(high_created_threshold, 1))
        + (updated_signal / max(high_updated_threshold, 1)),
    )
    failure_score = min(
        1.0,
        failure_rate + (failure_count_recent / max(failure_threshold, 1)),
    )

    raw_score = freshness_score + volume_score - failure_score
    normalized_score = _normalize_adaptive_score(raw_score)

    return {
        "freshness_score": round(freshness_score, 3),
        "volume_score": round(volume_score, 3),
        "failure_score": round(failure_score, 3),
        "raw_score": round(raw_score, 3),
        "score": round(normalized_score, 3),
    }


def compute_adaptive_interval(source, state, metrics):
    source_key = normalize_source(source)
    config = get_source_config(source_key)
    schedule_seconds = _coerce_positive_int(state.get("schedule_seconds"), 60 * 60)
    stale_schedule_seconds = _coerce_positive_int(
        state.get("stale_schedule_seconds"),
        max(schedule_seconds // 2, 60),
    )
    failure_retry_seconds = _coerce_positive_int(
        state.get("failure_retry_seconds"),
        max(schedule_seconds // 2, 60),
    )
    base_interval_seconds = _coerce_positive_int(
        state.get("base_interval_seconds"),
        schedule_seconds,
    )
    min_interval_seconds = _coerce_positive_int(
        config.get("adaptive_min_interval_seconds"),
        MIN_ADAPTIVE_INTERVAL_SECONDS,
    )
    min_interval_seconds = max(min_interval_seconds, MIN_ADAPTIVE_INTERVAL_SECONDS)
    max_interval_seconds = _coerce_positive_int(
        config.get("adaptive_max_interval_seconds"),
        MAX_ADAPTIVE_INTERVAL_SECONDS,
    )
    max_interval_seconds = max(min_interval_seconds, min(max_interval_seconds, MAX_ADAPTIVE_INTERVAL_SECONDS))
    high_created_threshold = _coerce_positive_int(
        config.get("adaptive_high_created_avg"),
        DEFAULT_ADAPTIVE_HIGH_CREATED_AVG,
    )
    high_updated_threshold = _coerce_positive_int(
        config.get("adaptive_high_updated_avg"),
        max(DEFAULT_ADAPTIVE_HIGH_UPDATED_AVG, high_created_threshold),
    )
    zero_runs_threshold = _coerce_positive_int(
        config.get("adaptive_zero_runs_threshold"),
        DEFAULT_ADAPTIVE_ZERO_RUNS_THRESHOLD,
    )
    failure_threshold = _coerce_positive_int(
        config.get("adaptive_failure_threshold"),
        DEFAULT_ADAPTIVE_FAILURE_THRESHOLD,
    )
    hard_failure_rate_threshold = _coerce_ratio(
        config.get("adaptive_hard_failure_rate_threshold"),
        DEFAULT_ADAPTIVE_HARD_FAILURE_RATE_THRESHOLD,
    )
    score_speedup_threshold = _coerce_float(
        config.get("adaptive_score_speedup_threshold"),
        DEFAULT_ADAPTIVE_SCORE_SPEEDUP_THRESHOLD,
    )
    score_cooldown_threshold = _coerce_float(
        config.get("adaptive_score_cooldown_threshold"),
        DEFAULT_ADAPTIVE_SCORE_COOLDOWN_THRESHOLD,
    )
    adaptive_score = _build_adaptive_score(
        metrics,
        state,
        high_created_threshold=high_created_threshold,
        high_updated_threshold=high_updated_threshold,
        failure_threshold=failure_threshold,
    )
    metrics.update(
        {
            "adaptive_score": adaptive_score["score"],
            "adaptive_raw_score": adaptive_score["raw_score"],
            "freshness_score": adaptive_score["freshness_score"],
            "volume_score": adaptive_score["volume_score"],
            "failure_score": adaptive_score["failure_score"],
        }
    )

    interval_seconds = base_interval_seconds
    reason = state.get("reason", "scheduled")
    rules = []

    latest_run_status = state.get("latest_run_status")
    failure_count_recent = int(metrics.get("failure_count_recent", 0) or 0)
    failed_pages_recent = int(metrics.get("failed_pages_recent", 0) or 0)
    failure_rate = float(metrics.get("failure_rate", 0.0) or 0.0)
    recent_created_avg = float(metrics.get("recent_created_avg", 0.0) or 0.0)
    recent_updated_avg = float(metrics.get("recent_updated_avg", 0.0) or 0.0)
    consecutive_zero_runs = int(metrics.get("consecutive_zero_runs", 0) or 0)

    hard_failure_cooldown = failure_rate > hard_failure_rate_threshold
    if hard_failure_cooldown:
        interval_seconds = MAX_ADAPTIVE_INTERVAL_SECONDS
        reason = "adaptive_hard_failure_cooldown"
        rules.append("hard_failure_rate_cooldown")
    elif latest_run_status == PipelineRunStatus.FAILED:
        backoff_steps = max(failure_count_recent, 1)
        interval_seconds = min(
            max_interval_seconds,
            max(failure_retry_seconds, failure_retry_seconds * backoff_steps),
        )
        if backoff_steps > 1:
            reason = "adaptive_failure_backoff"
            rules.append("recent_failures_backoff")
        else:
            reason = "retry_after_failure"
            rules.append("latest_failure_retry")
    elif state.get("is_stale"):
        interval_seconds = min(interval_seconds, stale_schedule_seconds)
        reason = "stale"
        rules.append("stale_priority")
    elif consecutive_zero_runs >= zero_runs_threshold:
        zero_multiplier = min(
            MAX_ZERO_RUN_SLOWDOWN_MULTIPLIER,
            consecutive_zero_runs - zero_runs_threshold + 2,
        )
        interval_seconds = min(
            max_interval_seconds,
            max(interval_seconds, schedule_seconds * zero_multiplier),
        )
        reason = "adaptive_low_volume"
        rules.append("consecutive_zero_runs_slowdown")
    elif recent_created_avg >= high_created_threshold:
        interval_seconds = max(
            min_interval_seconds,
            min(interval_seconds, schedule_seconds // ADAPTIVE_CREATED_SPEEDUP_DIVISOR),
        )
        reason = "adaptive_high_created_volume"
        rules.append("high_created_volume_speedup")
    elif recent_updated_avg >= high_updated_threshold:
        interval_seconds = max(
            min_interval_seconds,
            min(
                interval_seconds,
                (schedule_seconds * ADAPTIVE_UPDATED_SPEEDUP_NUMERATOR)
                // ADAPTIVE_UPDATED_SPEEDUP_DENOMINATOR,
            ),
        )
        reason = "adaptive_high_updated_volume"
        rules.append("high_updated_volume_speedup")

    if (
        not hard_failure_cooldown
        and latest_run_status != PipelineRunStatus.FAILED
        and not state.get("is_stale")
        and (
            failure_count_recent >= failure_threshold
            or failed_pages_recent >= failure_threshold
        )
    ):
        interval_seconds = min(
            max_interval_seconds,
            max(
                interval_seconds,
                (schedule_seconds * ADAPTIVE_FAILURE_BACKOFF_NUMERATOR)
                // ADAPTIVE_FAILURE_BACKOFF_DENOMINATOR,
            ),
        )
        reason = "adaptive_recent_failures"
        rules.append("recent_failure_signals_backoff")

    if (
        not hard_failure_cooldown
        and not rules
        and latest_run_status != PipelineRunStatus.FAILED
        and not state.get("is_stale")
    ):
        cooldown_score = (
            adaptive_score["raw_score"]
            if score_cooldown_threshold < 0
            else adaptive_score["score"]
        )
        if adaptive_score["score"] >= score_speedup_threshold:
            interval_seconds = max(
                min_interval_seconds,
                min(
                    interval_seconds,
                    (schedule_seconds * ADAPTIVE_SCORE_SPEEDUP_NUMERATOR)
                    // ADAPTIVE_SCORE_SPEEDUP_DENOMINATOR,
                ),
            )
            reason = "adaptive_score_high_activity"
            rules.append("score_high_activity_speedup")
        elif cooldown_score <= score_cooldown_threshold:
            interval_seconds = min(
                max_interval_seconds,
                max(
                    interval_seconds,
                    (schedule_seconds * ADAPTIVE_SCORE_COOLDOWN_NUMERATOR)
                    // ADAPTIVE_SCORE_COOLDOWN_DENOMINATOR,
                ),
            )
            reason = "adaptive_score_cooldown"
            rules.append("score_failure_cooldown")

    interval_seconds = _clamp_interval_seconds(
        interval_seconds,
        min_seconds=min_interval_seconds,
        max_seconds=MAX_ADAPTIVE_INTERVAL_SECONDS if hard_failure_cooldown else max_interval_seconds,
    )

    logger.debug(
        "scheduler_decision_metrics",
        extra={
            "source": source_key,
            "mode": "adaptive_hybrid",
            "created_avg": recent_created_avg,
            "updated_avg": recent_updated_avg,
            "failures": failure_count_recent,
            "failure_rate": failure_rate,
            "score": adaptive_score["score"],
            "raw_score": adaptive_score["raw_score"],
            "adaptive_score": adaptive_score["score"],
            "adaptive_raw_score": adaptive_score["raw_score"],
            "freshness_score": adaptive_score["freshness_score"],
            "volume_score": adaptive_score["volume_score"],
            "failure_score": adaptive_score["failure_score"],
            "reason": reason,
            "interval": interval_seconds,
            "rules": rules,
        },
    )

    return {
        "interval_seconds": int(interval_seconds),
        "reason": reason,
        "rules": rules,
        "base_interval_seconds": int(base_interval_seconds),
        "min_interval_seconds": int(min_interval_seconds),
        "max_interval_seconds": int(max_interval_seconds),
    }


def get_source_schedule_state(source, *, now_value=None):
    source_key = normalize_source(source)
    now_value = now_value or timezone.now()
    config = get_source_config(source_key)
    latest_run = PipelineRun.objects.filter(source=source_key).order_by("-started_at", "-id").first()
    latest_activity_run = _latest_activity_run(source_key)
    last_run_at = _finished_at(latest_run)
    last_activity_at = _finished_at(latest_activity_run)
    stale_after_seconds = _coerce_positive_int(config.get("stale_after_seconds"), 12 * 60 * 60)
    schedule_seconds = _coerce_positive_int(config.get("schedule_seconds"), 60 * 60)
    stale_schedule_seconds = _coerce_positive_int(
        config.get("stale_schedule_seconds"),
        max(schedule_seconds // 2, 60),
    )
    failure_retry_seconds = _coerce_positive_int(
        config.get("failure_retry_seconds"),
        max(schedule_seconds // 2, 60),
    )
    max_duration_seconds = _get_max_duration_seconds(source_key)
    running_age_seconds = _running_age_seconds(latest_run, now_value=now_value)
    metrics = get_source_schedule_metrics(source_key)
    is_running_stale = (
        latest_run is not None
        and latest_run.status == PipelineRunStatus.RUNNING
        and running_age_seconds >= max_duration_seconds
    )
    is_stale = (
        last_activity_at is None
        or now_value - last_activity_at >= timedelta(seconds=stale_after_seconds)
    )
    metrics["freshness_lag"] = (
        int(max((now_value - last_activity_at).total_seconds(), 0))
        if last_activity_at
        else None
    )

    if latest_run and latest_run.status == PipelineRunStatus.RUNNING:
        next_run_at = latest_run.started_at + timedelta(seconds=max_duration_seconds)
        if is_running_stale:
            return {
                "source": source_key,
                "priority": get_source_priority(source_key),
                "is_due": True,
                "is_stale": True,
                "is_running_stale": True,
                "reason": "running_stale",
                "interval_seconds": max_duration_seconds,
                "last_run_at": last_run_at,
                "last_activity_at": last_activity_at,
                "next_run_at": now_value,
                "latest_run_status": latest_run.status,
                "running_age_seconds": running_age_seconds,
                "max_duration_seconds": max_duration_seconds,
                "base_interval_seconds": max_duration_seconds,
                "adaptive_rules": ["running_stale_recovery"],
                "schedule_metrics": metrics,
            }
        return {
            "source": source_key,
            "priority": get_source_priority(source_key),
            "is_due": False,
            "is_stale": is_stale,
            "is_running_stale": False,
            "reason": "running",
            "interval_seconds": schedule_seconds,
            "last_run_at": last_run_at,
            "last_activity_at": last_activity_at,
            "next_run_at": next_run_at,
            "latest_run_status": latest_run.status,
            "running_age_seconds": running_age_seconds,
            "max_duration_seconds": max_duration_seconds,
            "base_interval_seconds": schedule_seconds,
            "adaptive_rules": ["running_lockout"],
            "schedule_metrics": metrics,
        }

    interval_seconds = stale_schedule_seconds if is_stale else schedule_seconds
    reason = "stale" if is_stale else "scheduled"
    if latest_run and latest_run.status == PipelineRunStatus.FAILED:
        interval_seconds = failure_retry_seconds
        reason = "retry_after_failure"

    adaptive = compute_adaptive_interval(
        source_key,
        {
            "base_interval_seconds": interval_seconds,
            "schedule_seconds": schedule_seconds,
            "stale_schedule_seconds": stale_schedule_seconds,
            "failure_retry_seconds": failure_retry_seconds,
            "latest_run_status": latest_run.status if latest_run else None,
            "is_stale": is_stale,
            "reason": reason,
        },
        metrics,
    )
    base_interval_seconds = interval_seconds
    interval_seconds = adaptive["interval_seconds"]
    reason = adaptive["reason"]
    next_run_at = last_run_at + timedelta(seconds=interval_seconds) if last_run_at else now_value
    return {
        "source": source_key,
        "priority": get_source_priority(source_key),
        "is_due": last_run_at is None or now_value >= next_run_at,
        "is_stale": is_stale,
        "is_running_stale": False,
        "reason": reason,
        "interval_seconds": interval_seconds,
        "last_run_at": last_run_at,
        "last_activity_at": last_activity_at,
        "next_run_at": next_run_at,
        "latest_run_status": latest_run.status if latest_run else None,
        "running_age_seconds": running_age_seconds,
        "max_duration_seconds": max_duration_seconds,
        "base_interval_seconds": base_interval_seconds,
        "adaptive_rules": adaptive["rules"],
        "schedule_metrics": metrics,
    }


def _schedule_state_log_payload(state):
    return {
        "source": state["source"],
        "priority": state["priority"],
        "is_due": state["is_due"],
        "reason": state["reason"],
        "last_run_at": _isoformat_or_none(state["last_run_at"]),
        "next_run_at": _isoformat_or_none(state["next_run_at"]),
        "last_activity_at": _isoformat_or_none(state["last_activity_at"]),
        "latest_run_status": state["latest_run_status"],
        "is_running_stale": state["is_running_stale"],
        "running_age_seconds": round(float(state["running_age_seconds"] or 0), 2),
        "max_duration_seconds": state["max_duration_seconds"],
    }


def _scheduler_decision_log_extra(state):
    metrics = state.get("schedule_metrics") or {}
    return {
        "source": state["source"],
        "priority": state["priority"],
        "is_due": state["is_due"],
        "reason": state["reason"],
        "interval": state["interval_seconds"],
        "next_run_at": _isoformat_or_none(state["next_run_at"]),
        "latest_status": state["latest_run_status"],
        "score": metrics.get("adaptive_score"),
        "raw_score": metrics.get("adaptive_raw_score"),
        "adaptive_raw_score": metrics.get("adaptive_raw_score"),
        "failure_rate": metrics.get("failure_rate"),
        "created_avg": metrics.get("recent_created_avg"),
        "updated_avg": metrics.get("recent_updated_avg"),
    }


def _record_scheduler_decision_timestamp(state):
    try:
        SourceSchedulerState.objects.update_or_create(
            source=state["source"],
            defaults={
                "last_decision_at": timezone.now(),
                "last_reason": str(state.get("reason") or "")[:80],
            },
        )
    except Exception:
        logger.exception("Could not persist scheduler decision timestamp source=%s", state.get("source"))


def _log_schedule_decisions(states, *, level=logging.INFO):
    for state in states:
        cache_scheduler_decision_snapshot(state)
        _record_scheduler_decision_timestamp(state)
        logger.log(level, "scheduler_decision", extra=_scheduler_decision_log_extra(state))
        logger.debug("scheduler_decision_state", extra=_schedule_state_log_payload(state))


def record_source_schedule_decision(source, *, now_value=None, level=logging.INFO):
    state = get_source_schedule_state(source, now_value=now_value)
    _log_schedule_decisions([state], level=level)
    return state


def mark_stale_running_runs(source, *, now_value=None):
    source_key = normalize_source(source)
    now_value = now_value or timezone.now()
    max_duration_seconds = _get_max_duration_seconds(source_key)
    stale_before = now_value - timedelta(seconds=max_duration_seconds)
    stale_runs = list(
        PipelineRun.objects.filter(
            source=source_key,
            status=PipelineRunStatus.RUNNING,
            started_at__lte=stale_before,
        )
    )

    for run in stale_runs:
        run.status = PipelineRunStatus.FAILED
        run.finished_at = now_value
        run.duration_seconds = max((now_value - run.started_at).total_seconds(), 0.0)
        run.error_message = (
            f"Marked failed before relaunch because it exceeded "
            f"max_duration_seconds={max_duration_seconds}."
        )
        run.save(update_fields=["status", "finished_at", "duration_seconds", "error_message"])
        logger.warning(
            "Marked stale running pipeline run as failed source=%s run_id=%s "
            "duration_seconds=%.2f max_duration_seconds=%s",
            source_key,
            run.pk,
            run.duration_seconds,
            max_duration_seconds,
        )

    return stale_runs


def select_sources_for_pipeline(sources=None, *, respect_schedule=False, now_value=None):
    now_value = now_value or timezone.now()
    configured_sources = sort_sources_by_priority(sources) if sources else get_configured_sources()

    if not configured_sources:
        logger.error(
            "Opportunity pipeline cannot run: no sources configured. "
            "Check OPPORTUNITY_PIPELINE_SOURCES."
        )
        raise CommandError("No opportunity sources configured.")

    if not respect_schedule:
        states = [
            get_source_schedule_state(source, now_value=now_value)
            for source in configured_sources
        ]
        _log_schedule_decisions(states)
        logger.info(
            "Opportunity pipeline schedule bypassed; running all selected sources=%s",
            configured_sources,
        )
        return configured_sources

    states = [
        get_source_schedule_state(source, now_value=now_value)
        for source in configured_sources
    ]
    due_sources = [state["source"] for state in states if state["is_due"]]

    if due_sources:
        _log_schedule_decisions(states)
        return due_sources

    # With respect_schedule=True, an idle schedule should stay idle. Manual
    # force-runs use respect_schedule=False or the Celery force flag instead.
    logger.info(
        "No opportunity sources are due; schedule respected. sources=%s",
        [state["source"] for state in states],
    )
    _log_schedule_decisions(states)
    return []


def get_due_source_schedule_states(sources=None, *, force=False, now_value=None):
    now_value = now_value or timezone.now()
    selected_sources = sort_sources_by_priority(sources) if sources else get_configured_sources()
    states = [
        get_source_schedule_state(source, now_value=now_value)
        for source in selected_sources
    ]
    _log_schedule_decisions(states)

    if force:
        return states
    return [state for state in states if state["is_due"]]


def get_due_sources(sources=None, *, force=False, now_value=None):
    return [
        state["source"]
        for state in get_due_source_schedule_states(
            sources,
            force=force,
            now_value=now_value,
        )
    ]


def get_scheduler_max_sources_per_tick(candidate_count=None):
    configured = _coerce_positive_int(
        getattr(settings, "OPPORTUNITY_SCHEDULER_MAX_SOURCES_PER_TICK", 0),
        0,
    )
    if configured <= 0:
        return candidate_count
    return configured


def get_scheduler_dispatch_dedup_seconds(source):
    source_key = normalize_source(source)
    config = get_source_config(source_key)
    configured = config.get(
        "dispatch_dedup_seconds",
        getattr(settings, "OPPORTUNITY_SCHEDULER_DISPATCH_DEDUP_SECONDS", MIN_ADAPTIVE_INTERVAL_SECONDS),
    )
    return max(
        MIN_ADAPTIVE_INTERVAL_SECONDS,
        _coerce_positive_int(configured, MIN_ADAPTIVE_INTERVAL_SECONDS),
    )


def reserve_source_dispatch(source, *, state=None, now_value=None):
    source_key = normalize_source(source)
    now_value = now_value or timezone.now()
    dedup_seconds = get_scheduler_dispatch_dedup_seconds(source_key)

    with transaction.atomic():
        scheduler_state, _ = (
            SourceSchedulerState.objects.select_for_update()
            .get_or_create(source=source_key)
        )
        if scheduler_state.last_dispatched_at:
            age_seconds = max((now_value - scheduler_state.last_dispatched_at).total_seconds(), 0.0)
            if age_seconds < dedup_seconds:
                return {
                    "reserved": False,
                    "reason": "recently_dispatched",
                    "source": source_key,
                    "last_dispatched_at": scheduler_state.last_dispatched_at,
                    "dedup_seconds": dedup_seconds,
                }

        running_run = (
            PipelineRun.objects.select_for_update()
            .filter(source=source_key, status=PipelineRunStatus.RUNNING)
            .order_by("-started_at", "-id")
            .first()
        )
        if running_run is not None:
            running_age_seconds = _running_age_seconds(running_run, now_value=now_value)
            if running_age_seconds < _get_max_duration_seconds(source_key):
                return {
                    "reserved": False,
                    "reason": "running",
                    "source": source_key,
                    "run_id": running_run.pk,
                    "running_age_seconds": running_age_seconds,
                }

        scheduler_state.last_dispatched_at = now_value
        scheduler_state.last_decision_at = now_value
        scheduler_state.last_reason = str((state or {}).get("reason") or "")[:80]
        scheduler_state.save(
            update_fields=[
                "last_dispatched_at",
                "last_decision_at",
                "last_reason",
                "updated_at",
            ]
        )

    return {
        "reserved": True,
        "reason": "reserved",
        "source": source_key,
        "last_dispatched_at": now_value,
        "dedup_seconds": dedup_seconds,
    }


def build_collection_result(source, stats, *, started_at, finished_at, status="completed", error_message=None):
    total_created = int(stats.get("created", 0) or 0)
    total_updated = int(stats.get("updated", 0) or 0)
    total_skipped = int(stats.get("skipped", 0) or 0)
    total_failed_pages = int(stats.get("failed_pages", 0) or 0)
    total_processed = total_created + total_updated + total_skipped
    duration_seconds = max((finished_at - started_at).total_seconds(), 0.0)
    # A source is stale only when it produced neither new nor refreshed records.
    is_stale = total_created == 0 and total_updated == 0

    return {
        "status": status,
        "source": source,
        "processed": total_processed,
        "created": total_created,
        "updated": total_updated,
        "skipped": total_skipped,
        "failed_pages": total_failed_pages,
        "is_stale": is_stale,
        "duration_seconds": duration_seconds,
        "error_message": error_message,
    }


def run_opportunity_pipeline(sources=None, *, respect_schedule=False, **options):
    selected_sources = select_sources_for_pipeline(
        sources,
        respect_schedule=respect_schedule,
    )

    results = []
    for source in selected_sources:
        stale_runs = mark_stale_running_runs(source)
        if stale_runs:
            logger.warning(
                "Relaunching source after stale running run cleanup source=%s stale_runs=%s",
                source,
                [run.pk for run in stale_runs],
            )
        logger.info("Running opportunity source pipeline source=%s", source)
        started_at = timezone.now()
        collection = run_source_collection(source, **options)
        finished_at = timezone.now()
        results.append(
            {
                **collection,
                "result": build_collection_result(
                    collection["source"],
                    collection["stats"],
                    started_at=started_at,
                    finished_at=finished_at,
                ),
            }
        )
    return results


# Clear scheduler-facing aliases. Keep the historical name available while
# making the module responsibility explicit for new callers.
run_pipeline = run_opportunity_pipeline
run_scheduler = run_pipeline
