import json
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from opportunities.locks import get_pipeline_lock_key, opportunity_pipeline_redis_client
from opportunities.models import Opportunite, PipelineRun, PipelineRunStatus
from opportunities.pipeline import (
    get_configured_sources,
    get_source_config,
    get_source_schedule_state,
    normalize_source,
)


logger = logging.getLogger(__name__)

INFO = "INFO"
WARNING = "WARNING"
CRITICAL = "CRITICAL"

SEVERITY_RANK = {
    INFO: 0,
    WARNING: 1,
    CRITICAL: 2,
}


def _setting_int(name, default):
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _setting_float(name, default):
    try:
        return float(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _cache_key(issue_key):
    return f"opportunity_pipeline_alert:{issue_key}"


def _get_alert_state(issue_key):
    key = _cache_key(issue_key)
    try:
        raw_state = opportunity_pipeline_redis_client().get(key)
        if raw_state:
            return json.loads(raw_state)
    except Exception:
        logger.exception("Could not read alert state from Redis issue=%s", issue_key)
    return cache.get(key) or {}


def _set_alert_state(issue_key, state, *, timeout):
    key = _cache_key(issue_key)
    try:
        opportunity_pipeline_redis_client().set(key, json.dumps(state, default=str), ex=timeout)
        return
    except Exception:
        logger.exception("Could not write alert state to Redis issue=%s", issue_key)
    cache.set(key, state, timeout=timeout)


def _delete_alert_state(issue_key):
    key = _cache_key(issue_key)
    try:
        opportunity_pipeline_redis_client().delete(key)
    except Exception:
        logger.exception("Could not delete alert state from Redis issue=%s", issue_key)
    cache.delete(key)


def _parse_dt(value):
    if not value:
        return None
    if hasattr(value, "utcoffset"):
        return value
    parsed = parse_datetime(str(value))
    return parsed if parsed else None


def _seconds_since(value, now_value):
    parsed = _parse_dt(value)
    if parsed is None:
        return None
    return max((now_value - parsed).total_seconds(), 0.0)


def _alerts_enabled():
    return bool(
        getattr(settings, "OPPORTUNITY_ALERTS_ENABLED", True)
        and getattr(settings, "OPPORTUNITY_ALERT_DISCORD_WEBHOOK_URL", "")
    )


def log_structured_event(event, severity=INFO, **payload):
    body = {
        "event": event,
        "severity": severity,
        "timestamp": timezone.now().isoformat(),
        **payload,
    }
    logger.info(json.dumps(body, sort_keys=True, default=str))


ALERT_COPY = {
    "No new opportunities detected": {
        "summary": "A source has not produced new opportunities within its expected freshness window.",
        "impact": "Candidates may see older results from this source until the next successful import.",
        "action": "Check the latest scraper run, source availability, and whether the source simply has no new listings.",
    },
    "Source freshness recovered": {
        "summary": "The source produced new opportunities again.",
        "impact": "The freshness issue is resolved and the dashboard can trust recent data from this source.",
        "action": "No action is required unless this alert repeats frequently.",
    },
    "Source failed repeatedly": {
        "summary": "The same source failed several times in a row.",
        "impact": "New opportunities from this source are not being imported.",
        "action": "Review scraper logs and retry after fixing the source-specific error.",
    },
    "Pipeline source run stuck": {
        "summary": "A pipeline run has been running longer than expected.",
        "impact": "Scheduled imports may be delayed while this run is still active.",
        "action": "Inspect the worker process and restart the run if it is no longer progressing.",
    },
    "Scraping duration anomaly": {
        "summary": "The latest successful run took longer than the configured normal duration.",
        "impact": "Imports still worked, but the source may be slow or close to timing out.",
        "action": "Monitor the next run and check the source if the duration stays high.",
    },
}

SEVERITY_COLORS = {
    INFO: 0x2563EB,
    WARNING: 0xD97706,
    CRITICAL: 0xDC2626,
    "RECOVERY": 0x16A34A,
}

SEVERITY_LABELS = {
    INFO: "Info",
    WARNING: "Warning",
    CRITICAL: "Critical",
    "RECOVERY": "Recovered",
}

DETAIL_LABELS = {
    "last_activity_at": "Last source activity",
    "started_at": "Run started at",
    "failed_runs": "Failed runs",
    "duration": "Duration",
    "threshold": "Expected maximum",
    "occurrences": "Times detected",
}


def _humanize_detail_value(value):
    if value in (None, "", "never"):
        return "No successful import with new opportunities yet"
    return str(value)


def _parse_alert_details(details):
    parsed = []
    for raw_line in str(details or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for token in line.split():
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            parsed.append((key.strip(), value.strip()))
    return parsed


def _build_discord_payload(*, severity, title, details="", source=None, recovery=False, occurrences=None):
    status = "RECOVERY" if recovery else severity
    copy = ALERT_COPY.get(title, {})
    parsed_details = _parse_alert_details(details)

    fields = [
        {
            "name": "Status",
            "value": SEVERITY_LABELS.get(status, str(status).title()),
            "inline": True,
        }
    ]
    if source:
        fields.append({"name": "Source", "value": str(source), "inline": True})
    if occurrences:
        fields.append({"name": "Times detected", "value": str(occurrences), "inline": True})

    for key, value in parsed_details:
        if key == "occurrences" and occurrences:
            continue
        fields.append(
            {
                "name": DETAIL_LABELS.get(key, key.replace("_", " ").title()),
                "value": _humanize_detail_value(value),
                "inline": True,
            }
        )

    if copy.get("impact"):
        fields.append({"name": "Impact", "value": copy["impact"], "inline": False})
    if copy.get("action"):
        fields.append({"name": "Recommended action", "value": copy["action"], "inline": False})

    if details and not parsed_details:
        fields.append({"name": "Details", "value": str(details)[:900], "inline": False})

    embed = {
        "title": title,
        "description": copy.get("summary") or "BidWise monitoring detected a pipeline event.",
        "color": SEVERITY_COLORS.get(status, SEVERITY_COLORS[INFO]),
        "fields": fields[:25],
        "footer": {"text": "BidWise monitoring"},
        "timestamp": timezone.now().isoformat(),
    }

    content = f"BidWise monitoring: {SEVERITY_LABELS.get(status, status)}"
    return {"content": content[:1900], "embeds": [embed]}


def _send_discord_alert(*, severity, title, details="", source=None, recovery=False, occurrences=None):
    payload = _build_discord_payload(
        severity=severity,
        title=title,
        details=details,
        source=source,
        recovery=recovery,
        occurrences=occurrences,
    )

    if not _alerts_enabled():
        logger.info("Discord alert suppressed: %s", json.dumps(payload, sort_keys=True, default=str))
        return False

    webhook_url = settings.OPPORTUNITY_ALERT_DISCORD_WEBHOOK_URL
    timeout = _setting_float("OPPORTUNITY_ALERT_REQUEST_TIMEOUT_SECONDS", 5.0)
    try:
        response = requests.post(webhook_url, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Discord alert delivery failed severity=%s source=%s", severity, source)
        return False
    return True


def record_issue(issue_key, *, severity, title, details="", source=None, threshold=None):
    threshold = threshold or _setting_int("OPPORTUNITY_ALERT_FAILURE_THRESHOLD", 3)
    cooldown_seconds = _setting_int("OPPORTUNITY_ALERT_COOLDOWN_SECONDS", 60 * 60)
    ttl_seconds = _setting_int("OPPORTUNITY_ALERT_STATE_TTL_SECONDS", 7 * 24 * 60 * 60)
    now_value = timezone.now()
    state = _get_alert_state(issue_key)
    count = int(state.get("count", 0) or 0) + 1
    last_alert_age = _seconds_since(state.get("last_alert_at"), now_value)
    active = bool(state.get("active"))

    should_alert = count >= threshold and (
        not active
        or last_alert_age is None
        or last_alert_age >= cooldown_seconds
    )

    state.update(
        {
            "count": count,
            "active": active or count >= threshold,
            "severity": severity,
            "title": title,
            "details": details,
            "source": source,
            "last_seen_at": now_value.isoformat(),
        }
    )
    if should_alert:
        _send_discord_alert(
            severity=severity,
            title=title,
            details=details,
            source=source,
            occurrences=count if count > threshold else None,
        )
        state["last_alert_at"] = now_value.isoformat()

    _set_alert_state(issue_key, state, timeout=ttl_seconds)
    return state


def record_recovery(issue_key, *, title, details="", source=None):
    state = _get_alert_state(issue_key)
    if not state:
        return False

    if state.get("active"):
        _send_discord_alert(
            severity=INFO,
            title=title,
            details=details,
            source=source or state.get("source"),
            recovery=True,
        )
    _delete_alert_state(issue_key)
    return True


def _failed_streak(source, limit):
    runs = list(PipelineRun.objects.filter(source=source).order_by("-started_at", "-id")[:limit])
    if not runs:
        return 0

    streak = 0
    for run in runs:
        if run.status != PipelineRunStatus.FAILED:
            break
        streak += 1
    return streak


def _duration_anomaly(source):
    max_duration = _setting_int(
        f"{source.upper()}_MAX_DURATION_SECONDS",
        get_source_config(source).get("max_duration_seconds", 0),
    )
    if not max_duration:
        return None

    latest_success = (
        PipelineRun.objects.filter(source=source, status=PipelineRunStatus.SUCCESS)
        .order_by("-started_at", "-id")
        .first()
    )
    if latest_success and latest_success.duration_seconds > max_duration:
        return {
            "issue_key": f"source:{source}:duration",
            "severity": WARNING,
            "source": source,
            "title": "Scraping duration anomaly",
            "details": (
                f"duration={latest_success.duration_seconds:.1f}s "
                f"threshold={max_duration}s"
            ),
        }
    return None


def collect_pipeline_anomalies(*, now_value=None):
    now_value = now_value or timezone.now()
    anomalies = []
    failed_threshold = _setting_int("OPPORTUNITY_ALERT_FAILURE_THRESHOLD", 3)

    stuck_cutoff = now_value - timedelta(
        seconds=_setting_int("OPPORTUNITY_PIPELINE_STUCK_SECONDS", 2 * 60 * 60)
    )
    stuck_runs = PipelineRun.objects.filter(
        status=PipelineRunStatus.RUNNING,
        started_at__lt=stuck_cutoff,
    ).order_by("started_at")
    for run in stuck_runs:
        anomalies.append(
            {
                "issue_key": f"source:{run.source}:stuck",
                "severity": CRITICAL,
                "source": run.source,
                "title": "Pipeline source run stuck",
                "details": f"started_at={run.started_at.isoformat()}",
            }
        )

    for source in get_configured_sources():
        state = get_source_schedule_state(source, now_value=now_value)
        if state["is_stale"]:
            last_activity = state["last_activity_at"].isoformat() if state["last_activity_at"] else "never"
            anomalies.append(
                {
                    "issue_key": f"source:{source}:no_new_jobs",
                    "severity": WARNING,
                    "source": source,
                    "title": "No new opportunities detected",
                    "details": f"last_activity_at={last_activity}",
                }
            )

        streak = _failed_streak(source, failed_threshold)
        if streak >= failed_threshold:
            anomalies.append(
                {
                    "issue_key": f"source:{source}:failed",
                    "severity": CRITICAL,
                    "source": source,
                    "title": "Source failed repeatedly",
                    "details": f"failed_runs={streak}",
                }
            )

        duration_anomaly = _duration_anomaly(source)
        if duration_anomaly:
            anomalies.append(duration_anomaly)

    missing_embeddings = Opportunite.objects.filter(embedding_vector__isnull=True).count()
    embedding_threshold = _setting_int("OPPORTUNITY_EMBEDDING_ALERT_THRESHOLD", 100)
    if missing_embeddings >= embedding_threshold:
        anomalies.append(
            {
                "issue_key": "embeddings:backlog",
                "severity": WARNING,
                "source": None,
                "title": "Embedding backlog detected",
                "details": f"missing_embeddings={missing_embeddings}",
            }
        )

    return sorted(
        anomalies,
        key=lambda item: (-SEVERITY_RANK.get(item["severity"], 0), item.get("source") or ""),
    )


def _known_issue_keys():
    keys = {"embeddings:backlog", "embeddings:no_progress"}
    for source in get_configured_sources():
        keys.update(
            {
                f"source:{source}:failed",
                f"source:{source}:no_new_jobs",
                f"source:{source}:duration",
                f"source:{source}:stuck",
            }
        )
    return keys


def recover_stuck_pipeline_runs(*, now_value=None):
    if not getattr(settings, "OPPORTUNITY_AUTO_RECOVERY_ENABLED", True):
        return 0

    now_value = now_value or timezone.now()
    stuck_cutoff = now_value - timedelta(
        seconds=_setting_int("OPPORTUNITY_PIPELINE_STUCK_SECONDS", 2 * 60 * 60)
    )
    stuck_runs = list(
        PipelineRun.objects.filter(
            status=PipelineRunStatus.RUNNING,
            started_at__lt=stuck_cutoff,
        )
    )
    if not stuck_runs:
        return 0

    try:
        client = opportunity_pipeline_redis_client()
    except Exception:
        logger.exception("Pipeline auto-recovery could not connect to Redis")
        client = None

    recovered = 0
    for run in stuck_runs:
        source = normalize_source(run.source) if run.source else None
        run.status = PipelineRunStatus.FAILED
        run.finished_at = now_value
        run.duration_seconds = max((now_value - run.started_at).total_seconds(), 0.0)
        run.error_message = "Auto-recovered after being stuck."
        run.save(update_fields=["status", "finished_at", "duration_seconds", "error_message"])
        if client and source:
            try:
                client.delete(get_pipeline_lock_key(source))
            except Exception:
                logger.exception("Pipeline auto-recovery could not reset Redis lock source=%s", source)
        recovered += 1

    return recovered


def evaluate_pipeline_health():
    anomalies = collect_pipeline_anomalies()
    active_issue_keys = {item["issue_key"] for item in anomalies}
    for anomaly in anomalies:
        threshold = 1 if anomaly["issue_key"].endswith(":stuck") else None
        record_issue(
            anomaly["issue_key"],
            severity=anomaly["severity"],
            title=anomaly["title"],
            details=anomaly["details"],
            source=anomaly.get("source"),
            threshold=threshold,
        )

    for issue_key in _known_issue_keys() - active_issue_keys:
        record_recovery(
            issue_key,
            title="Pipeline issue recovered",
            details=f"issue={issue_key}",
        )

    recovered = recover_stuck_pipeline_runs()
    status = CRITICAL if any(item["severity"] == CRITICAL for item in anomalies) else INFO
    log_structured_event(
        "pipeline_health_check",
        severity=status,
        anomalies=len(anomalies),
        recovered=recovered,
    )
    return {
        "status": "degraded" if anomalies else "healthy",
        "alerts": anomalies,
        "recovered": recovered,
    }


def observe_source_run(source, result, *, pipeline_status):
    severity = CRITICAL if pipeline_status == PipelineRunStatus.FAILED else INFO
    log_structured_event(
        "source_run",
        severity=severity,
        source=source,
        duration=result.get("duration_seconds", 0),
        created=result.get("created", 0),
        updated=result.get("updated", 0),
        skipped=result.get("skipped", 0),
        failed_pages=result.get("failed_pages", 0),
        status=result.get("status"),
    )

    if pipeline_status == PipelineRunStatus.FAILED:
        record_issue(
            f"source:{source}:failed",
            severity=CRITICAL,
            title="Source collection failed",
            details=result.get("error_message") or "source run failed",
            source=source,
        )
    else:
        record_recovery(
            f"source:{source}:failed",
            title="Source collection recovered",
            details="latest run completed successfully",
            source=source,
        )

    duration_anomaly = _duration_anomaly(source)
    if duration_anomaly:
        record_issue(
            duration_anomaly["issue_key"],
            severity=duration_anomaly["severity"],
            title=duration_anomaly["title"],
            details=duration_anomaly["details"],
            source=source,
        )
    else:
        record_recovery(
            f"source:{source}:duration",
            title="Scraping duration back to normal",
            details="latest run duration is within threshold",
            source=source,
        )

    schedule_state = get_source_schedule_state(source)
    if schedule_state["is_stale"]:
        record_issue(
            f"source:{source}:no_new_jobs",
            severity=WARNING,
            title="No new opportunities detected",
            details=(
                f"last_activity_at="
                f"{schedule_state['last_activity_at'].isoformat() if schedule_state['last_activity_at'] else 'never'}"
            ),
            source=source,
        )
    else:
        record_recovery(
            f"source:{source}:no_new_jobs",
            title="Source freshness recovered",
            details="new opportunities were detected recently",
            source=source,
        )
