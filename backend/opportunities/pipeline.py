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
from django.db.models import Q
from django.utils import timezone

from opportunities.models import PipelineRun, PipelineRunStatus
from opportunities.scraping.pipeline import run_collection
from opportunities.scraping.sources import (
    EmploiTunisieScraper,
    KeejobScraper,
    LinkedInScraper,
    MarchesPublicsScraper,
)


logger = logging.getLogger(__name__)

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


def _isoformat_or_none(value):
    return value.isoformat() if value else None


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
        "fetch_details": options.get("fetch_details"),
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
    is_running_stale = (
        latest_run is not None
        and latest_run.status == PipelineRunStatus.RUNNING
        and running_age_seconds >= max_duration_seconds
    )
    is_stale = (
        last_activity_at is None
        or now_value - last_activity_at >= timedelta(seconds=stale_after_seconds)
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
        }

    interval_seconds = stale_schedule_seconds if is_stale else schedule_seconds
    reason = "stale" if is_stale else "scheduled"
    if latest_run and latest_run.status == PipelineRunStatus.FAILED:
        interval_seconds = failure_retry_seconds
        reason = "retry_after_failure"

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


def _log_schedule_decisions(states, *, level=logging.INFO):
    for state in states:
        logger.log(
            level,
            "Opportunity source schedule decision source=%s due=%s reason=%s "
            "last_run_at=%s next_run_at=%s last_activity_at=%s latest_status=%s "
            "running_age_seconds=%.2f max_duration_seconds=%s",
            state["source"],
            state["is_due"],
            state["reason"],
            _isoformat_or_none(state["last_run_at"]),
            _isoformat_or_none(state["next_run_at"]),
            _isoformat_or_none(state["last_activity_at"]),
            state["latest_run_status"],
            float(state["running_age_seconds"] or 0),
            state["max_duration_seconds"],
        )


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
        "No opportunity sources are due; schedule respected. schedule_decisions=%s",
        [_schedule_state_log_payload(state) for state in states],
    )
    _log_schedule_decisions(states)
    return []


def get_due_sources(sources=None, *, force=False, now_value=None):
    selected_sources = sort_sources_by_priority(sources) if sources else get_configured_sources()
    if force:
        return selected_sources
    return [
        source
        for source in selected_sources
        if get_source_schedule_state(source, now_value=now_value)["is_due"]
    ]


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
