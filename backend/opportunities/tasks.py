import logging
import uuid
from datetime import timezone as datetime_timezone

from celery import shared_task
from django.conf import settings
from django.core.management import call_command
from django.core.mail import send_mail
from django.db import close_old_connections
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from .locks import (
    acquire_pipeline_lock,
    get_pipeline_lock_key,
    opportunity_pipeline_redis_client,
    release_pipeline_lock,
)
from .monitoring import (
    CRITICAL,
    evaluate_pipeline_health,
    log_structured_event,
    observe_source_run,
    record_issue,
    record_recovery,
)
from .pipeline import (
    build_collection_result,
    get_configured_sources,
    get_due_source_schedule_states,
    get_scheduler_max_sources_per_tick,
    get_source_config,
    normalize_source,
    record_source_schedule_decision,
    reserve_source_dispatch,
    run_source_collection,
)
from .models import (
    PipelineRun,
    PipelineRunStatus,
    Opportunite,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
)
from .organization_expiration import expire_due_organization_opportunities
from .organization_notification_emails import (
    build_admin_approved_email,
    build_admin_rejected_email,
)
from .processing import process_pending_raw_opportunities


logger = logging.getLogger(__name__)
MAX_FAILED_PAGES = 3
MATERIALIZATION_BATCH_SIZE = 100
MATERIALIZATION_RETRIGGER_COUNTDOWN_SECONDS = 2
EMBEDDING_RETRIGGER_COUNTDOWN_SECONDS = 10
DECISION_EMAIL_PROCESSING_STALE_SECONDS = 15 * 60


def _is_recent_processing_notification(notification):
    if notification.get("status") != "processing":
        return False
    started_at = parse_datetime(str(notification.get("started_at") or ""))
    if started_at is None:
        return False
    if timezone.is_naive(started_at):
        started_at = timezone.make_aware(started_at, timezone=datetime_timezone.utc)
    return (timezone.now() - started_at).total_seconds() < DECISION_EMAIL_PROCESSING_STALE_SECONDS


@shared_task(
    bind=True,
    name="opportunities.send_organization_admin_decision_email",
    max_retries=3,
)
def send_organization_admin_decision_email_task(
    self,
    opportunity_id,
    decision,
    decision_id,
):
    if decision not in {"approved", "rejected"}:
        logger.warning(
            "Organization decision email skipped opportunity_id=%s invalid_decision=%s",
            opportunity_id,
            decision,
        )
        return {"status": "skipped", "reason": "invalid_decision"}

    try:
        with transaction.atomic():
            opportunity = (
                Opportunite.objects.select_for_update()
                .filter(pk=opportunity_id)
                .first()
            )
            if opportunity is None or opportunity.organisation is None:
                return {"status": "skipped", "reason": "opportunity_or_recipient_missing"}

            extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
            moderation = extra_data.get("moderation")
            moderation = moderation if isinstance(moderation, dict) else {}
            admin_decision = moderation.get("admin_decision")
            admin_decision = admin_decision if isinstance(admin_decision, dict) else {}

            if (
                admin_decision.get("action") != decision
                or admin_decision.get("decided_at") != decision_id
            ):
                return {"status": "skipped", "reason": "stale_decision"}

            notification = admin_decision.get("email_notification")
            notification = notification if isinstance(notification, dict) else {}
            if notification.get("sent_at"):
                return {"status": "skipped", "reason": "already_sent"}
            if _is_recent_processing_notification(notification):
                return {"status": "skipped", "reason": "already_processing"}

            recipient = str(opportunity.organisation.email or "").strip()
            if not recipient:
                return {"status": "skipped", "reason": "recipient_missing"}

            notification.update({
                "status": "processing",
                "task_id": self.request.id or "",
                "started_at": timezone.now().isoformat(),
            })
            admin_decision["email_notification"] = notification
            moderation["admin_decision"] = admin_decision
            extra_data["moderation"] = moderation
            opportunity.extra_data = extra_data
            opportunity.save(update_fields=["extra_data"])

            if decision == "approved":
                email = build_admin_approved_email(opportunity)
            else:
                email = build_admin_rejected_email(
                    opportunity,
                    admin_note=admin_decision.get("note", ""),
                )

        send_mail(
            subject=email.subject,
            message=email.plaintext,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
            html_message=email.html,
        )

        with transaction.atomic():
            opportunity = Opportunite.objects.select_for_update().get(pk=opportunity_id)
            extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
            moderation = extra_data.get("moderation")
            moderation = moderation if isinstance(moderation, dict) else {}
            admin_decision = moderation.get("admin_decision")
            admin_decision = admin_decision if isinstance(admin_decision, dict) else {}
            if (
                admin_decision.get("action") == decision
                and admin_decision.get("decided_at") == decision_id
            ):
                notification = admin_decision.get("email_notification") or {}
                notification.update({
                    "status": "sent",
                    "sent_at": timezone.now().isoformat(),
                    "recipient": recipient,
                })
                admin_decision["email_notification"] = notification
                moderation["admin_decision"] = admin_decision
                extra_data["moderation"] = moderation
                opportunity.extra_data = extra_data
                opportunity.save(update_fields=["extra_data"])

        logger.info(
            "Organization decision email sent opportunity_id=%s decision=%s recipient=%s",
            opportunity_id,
            decision,
            recipient,
        )
        return {"status": "sent", "opportunity_id": opportunity_id, "decision": decision}
    except Exception as exc:
        with transaction.atomic():
            opportunity = Opportunite.objects.select_for_update().filter(pk=opportunity_id).first()
            if opportunity is not None:
                extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
                moderation = extra_data.get("moderation")
                moderation = moderation if isinstance(moderation, dict) else {}
                admin_decision = moderation.get("admin_decision")
                admin_decision = admin_decision if isinstance(admin_decision, dict) else {}
                if (
                    admin_decision.get("action") == decision
                    and admin_decision.get("decided_at") == decision_id
                ):
                    notification = admin_decision.get("email_notification") or {}
                    notification.update({
                        "status": "failed",
                        "last_error_at": timezone.now().isoformat(),
                    })
                    admin_decision["email_notification"] = notification
                    moderation["admin_decision"] = admin_decision
                    extra_data["moderation"] = moderation
                    opportunity.extra_data = extra_data
                    opportunity.save(update_fields=["extra_data"])
        logger.exception(
            "Organization decision email failed opportunity_id=%s decision=%s",
            opportunity_id,
            decision,
        )
        countdown = min(30 * (2 ** int(self.request.retries or 0)), 300)
        raise self.retry(exc=exc, countdown=countdown)


@shared_task(name="opportunities.expire_organization_opportunities")
def expire_organization_opportunities_task():
    result = expire_due_organization_opportunities()
    logger.info(
        "Organization opportunity expiration completed inspected=%s expired=%s by_reason=%s",
        result["inspected"],
        result["expired"],
        result["by_reason"],
    )
    return result


def _cleanup_stale_running_runs(source, *, finished_at):
    stale_runs = PipelineRun.objects.filter(
        source=source,
        status=PipelineRunStatus.RUNNING,
    )
    for stale_run in stale_runs.iterator():
        stale_run.status = PipelineRunStatus.FAILED
        stale_run.finished_at = finished_at
        stale_run.duration_seconds = max((finished_at - stale_run.started_at).total_seconds(), 0.0)
        stale_run.error_message = "Marked failed because a new source run started."
        stale_run.save(
            update_fields=[
                "status",
                "finished_at",
                "duration_seconds",
                "error_message",
            ]
        )


def _finalize_pipeline_run(
    pipeline_run,
    *,
    status,
    finished_at,
    result=None,
    error_message=None,
    is_stale=False,
):
    pipeline_run.status = status
    pipeline_run.finished_at = finished_at
    pipeline_run.duration_seconds = max((finished_at - pipeline_run.started_at).total_seconds(), 0.0)

    if result is not None:
        total_processed = int(result.get("processed", 0) or 0)
        total_created = int(result.get("created", 0) or 0)
        total_updated = int(result.get("updated", 0) or 0)
        total_failed_pages = int(result.get("failed_pages", 0) or 0)
        pipeline_run.processed_count = total_processed
        pipeline_run.created_count = total_created
        pipeline_run.updated_count = total_updated
        pipeline_run.total_processed = total_processed
        pipeline_run.total_created = total_created
        pipeline_run.total_updated = total_updated
        pipeline_run.total_failed_pages = total_failed_pages
        pipeline_run.is_stale = bool(result.get("is_stale", is_stale))
    else:
        pipeline_run.is_stale = bool(is_stale)

    pipeline_run.error_message = error_message
    pipeline_run.save(
        update_fields=[
            "status",
            "finished_at",
            "duration_seconds",
            "processed_count",
            "created_count",
            "updated_count",
            "total_processed",
            "total_created",
            "total_updated",
            "total_failed_pages",
            "is_stale",
            "error_message",
        ]
    )


def _record_source_schedule_decision_safely(source, *, level=logging.INFO):
    try:
        if level == logging.INFO:
            record_source_schedule_decision(source)
        else:
            record_source_schedule_decision(source, level=level)
    except Exception:
        logger.exception("Could not record scheduler decision for source=%s", source)


@shared_task(
    bind=True,
    name="opportunities.collect_opportunities",
    max_retries=0,
)
def collect_opportunities_pipeline(self, force=False, sources=None, **command_options):
    task_id = self.request.id or "manual"
    if isinstance(sources, str):
        configured_sources = [sources]
    else:
        configured_sources = sources or get_configured_sources()
    due_states = get_due_source_schedule_states(configured_sources, force=force)
    dispatch_limit = get_scheduler_max_sources_per_tick(len(due_states))
    dispatched_sources = []
    skipped_sources = []
    logger.info(
        "Dispatching opportunity pipeline task_id=%s sources=%s due_sources=%s force=%s max_sources_per_tick=%s",
        task_id,
        configured_sources,
        [state["source"] for state in due_states],
        force,
        dispatch_limit,
    )
    for state in due_states:
        source = state["source"]
        if dispatch_limit is not None and len(dispatched_sources) >= dispatch_limit:
            skipped_sources.append({"source": source, "reason": "dispatch_limit"})
            logger.info(
                "Opportunity source dispatch skipped task_id=%s source=%s reason=dispatch_limit max_sources_per_tick=%s",
                task_id,
                source,
                dispatch_limit,
                extra={
                    "task_id": task_id,
                    "source": source,
                    "reason": "dispatch_limit",
                    "max_sources_per_tick": dispatch_limit,
                },
            )
            continue

        reservation = reserve_source_dispatch(source, state=state)
        if not reservation["reserved"]:
            skipped_sources.append({"source": source, "reason": reservation["reason"]})
            logger.info(
                "Opportunity source dispatch skipped task_id=%s source=%s reason=%s",
                task_id,
                source,
                reservation["reason"],
                extra={
                    "task_id": task_id,
                    "source": source,
                    "reason": reservation["reason"],
                    "dedup_seconds": reservation.get("dedup_seconds"),
                    "run_id": reservation.get("run_id"),
                },
            )
            continue

        log_structured_event(
            "source_dispatch",
            source=source,
            priority=state["priority"],
            reason=state["reason"],
            is_stale=state["is_stale"],
            task_id=task_id,
        )
        collect_source_task.apply_async(
            args=[source],
            kwargs={key: value for key, value in command_options.items() if value is not None},
        )
        dispatched_sources.append(source)

    status = "dispatched" if dispatched_sources else "skipped"
    return {
        "status": status,
        "sources": dispatched_sources,
        "configured_sources": configured_sources,
        "skipped_sources": skipped_sources,
    }


def _process_materialization_batch(batch_size=MATERIALIZATION_BATCH_SIZE):
    logger.info("materialization batch started")
    stats = process_pending_raw_opportunities(limit=min(batch_size, MATERIALIZATION_BATCH_SIZE))
    processed = int(stats.get("processed", 0) or 0)
    created = int(stats.get("created", 0) or 0)
    updated = int(stats.get("updated", 0) or 0)
    failed = int(stats.get("failed", 0) or 0)
    logger.info("processed %s records", processed)
    logger.info("created=%s updated=%s failed=%s", created, updated, failed)
    return stats


def _missing_embeddings_queryset():
    return Opportunite.objects.filter(embedding_vector__isnull=True)


def _schedule_embedding_generation_if_needed():
    if _missing_embeddings_queryset().exists():
        generate_embeddings_task.apply_async(countdown=EMBEDDING_RETRIGGER_COUNTDOWN_SECONDS)


@shared_task(
    bind=True,
    name="opportunities.materialize_opportunities",
    max_retries=0,
)
def materialize_opportunities_task(self):
    stats = _process_materialization_batch()
    remaining = RawOpportunite.objects.filter(
        processing_status=RawOpportuniteProcessingStatus.NEW,
    ).count()

    logger.info("remaining NEW records=%s", remaining)

    if remaining > 0:
        logger.info(
            "re-triggering materialization task countdown=%s",
            MATERIALIZATION_RETRIGGER_COUNTDOWN_SECONDS,
        )
        materialize_opportunities_task.apply_async(
            countdown=MATERIALIZATION_RETRIGGER_COUNTDOWN_SECONDS,
        )
    else:
        _schedule_embedding_generation_if_needed()

    return stats


@shared_task(
    bind=True,
    name="opportunities.generate_embeddings",
    max_retries=0,
)
def generate_embeddings_task(self):
    task_id = self.request.id or "manual"
    lock_key = "pipeline:embeddings:lock"
    lock_token = f"{task_id}:{uuid.uuid4()}"
    client = opportunity_pipeline_redis_client()

    if not acquire_pipeline_lock(client, lock_key, lock_token):
        logger.info(
            "Embedding generation task skipped task_id=%s reason=locked",
            task_id,
            extra={"task_id": task_id, "reason": "locked"},
        )
        return {"status": "skipped", "reason": "locked"}

    limit = int(getattr(settings, "OPPORTUNITY_EMBEDDING_TASK_LIMIT", 200))
    before_missing = _missing_embeddings_queryset().count()

    logger.info(
        "embedding generation batch started task_id=%s limit=%s missing_before=%s",
        task_id,
        limit,
        before_missing,
    )

    try:
        if before_missing <= 0:
            return {
                "status": "completed",
                "processed": 0,
                "remaining": 0,
            }

        call_command("generate_embeddings", limit=limit)
        remaining = _missing_embeddings_queryset().count()
        processed = max(before_missing - remaining, 0)
        logger.info(
            "embedding generation batch ended task_id=%s processed=%s remaining=%s",
            task_id,
            processed,
            remaining,
        )

        if remaining > 0 and processed > 0:
            logger.info(
                "re-triggering embedding generation task countdown=%s",
                EMBEDDING_RETRIGGER_COUNTDOWN_SECONDS,
            )
            generate_embeddings_task.apply_async(countdown=EMBEDDING_RETRIGGER_COUNTDOWN_SECONDS)
            record_recovery(
                "embeddings:no_progress",
                title="Embedding generation recovered",
                details="embedding task made progress",
            )
        elif remaining > 0:
            logger.warning(
                "embedding generation made no progress task_id=%s remaining=%s",
                task_id,
                remaining,
            )
            record_issue(
                "embeddings:no_progress",
                severity=CRITICAL,
                title="Embedding generation made no progress",
                details=f"remaining={remaining}",
            )

        return {
            "status": "completed",
            "processed": processed,
            "remaining": remaining,
        }
    finally:
        released = release_pipeline_lock(client, lock_key, lock_token)
        if not released:
            logger.warning(
                "Embedding generation lock was not released by owner task_id=%s",
                task_id,
                extra={"task_id": task_id, "lock_key": lock_key},
            )
        close_old_connections()


@shared_task(
    bind=True,
    name="opportunities.monitor_pipeline",
    max_retries=0,
)
def monitor_opportunity_pipeline_task(self):
    task_id = self.request.id or "manual"
    result = evaluate_pipeline_health()
    logger.info(
        "Opportunity pipeline monitor ended task_id=%s status=%s alerts=%s recovered=%s",
        task_id,
        result["status"],
        len(result["alerts"]),
        result["recovered"],
    )
    return result


@shared_task(
    bind=True,
    name="opportunities.collect_source",
    max_retries=3,
)
def collect_source_task(self, source, **command_options):
    source = normalize_source(source)
    task_id = self.request.id or "manual"
    lock_key = get_pipeline_lock_key(source)
    lock_token = f"{task_id}:{uuid.uuid4()}"
    client = opportunity_pipeline_redis_client()

    if not acquire_pipeline_lock(client, lock_key, lock_token):
        _record_source_schedule_decision_safely(source)
        logger.info(
            "Opportunity source task skipped task_id=%s source=%s reason=locked",
            task_id,
            source,
            extra={"task_id": task_id, "source": source, "reason": "locked"},
        )
        return {"status": "skipped", "reason": "locked", "source": source}

    started_at = timezone.now()
    _cleanup_stale_running_runs(source, finished_at=started_at)
    pipeline_run = PipelineRun.objects.create(
        started_at=started_at,
        status=PipelineRunStatus.RUNNING,
        source=source,
    )

    try:
        close_old_connections()
        logger.info(
            "Opportunity source task started task_id=%s source=%s",
            task_id,
            source,
            extra={"task_id": task_id, "source": source},
        )

        collection = run_source_collection(source, **command_options)
        stats = collection["stats"]
        finished_at = timezone.now()
        failed_pages = int(stats.get("failed_pages", 0) or 0)
        stopped_due_to_failures = bool(stats.get("stopped_due_to_failures", False))
        too_many_failed_pages = failed_pages >= MAX_FAILED_PAGES
        status = (
            PipelineRunStatus.FAILED
            if stopped_due_to_failures or too_many_failed_pages
            else PipelineRunStatus.SUCCESS
        )
        error_message = (
            f"Source stopped after {failed_pages} failed page(s)."
            if stopped_due_to_failures or too_many_failed_pages
            else None
        )
        result = build_collection_result(
            source,
            stats,
            started_at=started_at,
            finished_at=finished_at,
            status="failed" if stopped_due_to_failures or too_many_failed_pages else "completed",
            error_message=error_message,
        )
        if result["created"] == 0:
            logger.info("[%s] no new data detected", source)

        _finalize_pipeline_run(
            pipeline_run,
            status=status,
            finished_at=finished_at,
            result=result,
            error_message=error_message,
            is_stale=result["is_stale"],
        )
        logger.info(
            "Opportunity source task ended task_id=%s source=%s status=%s processed=%s "
            "created=%s updated=%s skipped=%s failed_pages=%s duration_seconds=%.2f",
            task_id,
            source,
            status,
            result["processed"],
            result["created"],
            result["updated"],
            result["skipped"],
            result["failed_pages"],
            result["duration_seconds"],
        )
        observe_source_run(source, result, pipeline_status=status)
        _record_source_schedule_decision_safely(source)
        if RawOpportunite.objects.filter(
            processing_status=RawOpportuniteProcessingStatus.NEW,
        ).exists():
            materialize_opportunities_task.apply_async(
                countdown=MATERIALIZATION_RETRIGGER_COUNTDOWN_SECONDS,
            )
        else:
            _schedule_embedding_generation_if_needed()
        return result
    except Exception as exc:
        finished_at = timezone.now()
        result = build_collection_result(
            source,
            {},
            started_at=started_at,
            finished_at=finished_at,
            status="failed",
            error_message=str(exc),
        )
        _finalize_pipeline_run(
            pipeline_run,
            status=PipelineRunStatus.FAILED,
            finished_at=finished_at,
            result=result,
            error_message=str(exc),
        )
        logger.exception(
            "Opportunity source task failed task_id=%s source=%s",
            task_id,
            source,
            extra={"task_id": task_id, "source": source},
        )
        observe_source_run(source, result, pipeline_status=PipelineRunStatus.FAILED)
        _record_source_schedule_decision_safely(source)
        request = getattr(self, "request", None)
        retries = int(getattr(request, "retries", 0) or 0)
        called_directly = bool(getattr(request, "called_directly", False))
        retry_limit = int(get_source_config(source).get("max_retries", 2) or 0)
        if not called_directly and retries < retry_limit:
            countdown = int(get_source_config(source).get("failure_retry_seconds", 60) or 60)
            raise self.retry(exc=exc, countdown=countdown, max_retries=retry_limit)
        return result
    finally:
        released = release_pipeline_lock(client, lock_key, lock_token)
        if not released:
            logger.warning(
                "Opportunity source lock was not released by owner task_id=%s source=%s",
                task_id,
                source,
                extra={"task_id": task_id, "source": source, "lock_key": lock_key},
            )
        close_old_connections()
