# Sprint 2 - Testing guide

Last updated: 2026-04-28

This guide validates the Sprint 2 opportunities pipeline for release or defense. It focuses on the production architecture that exists in the codebase: CLI collection, Celery orchestration, Beat scheduling, monitoring, alerting, stuck-run recovery, materialization, embeddings, API, and dashboard visibility.

## 1. Preconditions

From the repository root:

```bash
docker compose up -d
docker compose ps
```

Expected services:

- `backend` is `Up`
- `db` is healthy
- `redis` is healthy
- `celery_worker` is `Up`
- `celery_beat` is `Up`

Optional but useful:

```bash
docker compose logs --tail=80 celery_worker
docker compose logs --tail=80 celery_beat
```

Active source keys:

- `linkedin`
- `keejob`
- `emploi_tn`
- `marches_publics`

Dashboard surfaces:

- frontend page: `/dashboard-admin`
- backend endpoint: `/api/admin/dashboard/`

The dashboard requires an authenticated staff or superuser account.

## 2. Manual CLI execution test

Purpose: prove that manual execution uses the same source registry, source options, scraper construction, raw shadow storage, and schedule logic as the production pipeline core.

### Command

```bash
docker compose run --rm backend python manage.py collect_opportunities --source keejob --max-pages 1 --max-records 5 --timeout 15 --min-delay 0.1 --max-delay 0.2
```

Optional scheduler-aware variant:

```bash
docker compose run --rm backend python manage.py collect_opportunities --source keejob --respect-schedule --max-pages 1 --max-records 5
```

Process pending raw records after manual collection:

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.processing import process_pending_raw_opportunities; print(process_pending_raw_opportunities(limit=100))"
```

### Expected behavior

- CLI prints source start information and final collection stats.
- `Created`, `Updated`, `Skipped`, and `Failed pages` are reported per source.
- Raw records are stored in `RawOpportunite`.
- Processing converts `NEW` raw records into canonical `Opportunite` rows or marks invalid rows as `REJECTED`.
- A manual CLI collection does not create a production `PipelineRun`; the Celery source task owns `PipelineRun` lifecycle.

### What to show on dashboard

- `Pipeline Lag` may increase after collection if raw `NEW` records exist.
- `Pipeline Lag` should decrease after processing.
- `Opportunities by Source` should include or update the source volume.
- `AI Readiness` may show missing embeddings until embedding generation runs.

### What to explain orally

The CLI is an operator tool for controlled collection and smoke tests. It reuses the same pipeline core as Celery for source selection, aliases, scraper options, schedule decisions, and raw ingestion. The full production DAG is handled by Celery because that path records `PipelineRun`, applies locks, retries, materializes, embeds, and monitors.

## 3. Celery async execution test

Purpose: prove that production execution is asynchronous and source-scoped.

### Command

Dispatch one forced source run:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.tasks import collect_opportunities_pipeline; task=collect_opportunities_pipeline.delay(force=True, sources=['keejob'], max_pages=1, max_records=5); print(task.id)"
```

Watch worker logs:

```bash
docker compose logs --tail=120 celery_worker
```

Inspect latest pipeline run:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.models import PipelineRun; run=PipelineRun.objects.order_by('-started_at').first(); print({'source': run.source, 'status': run.status, 'processed': run.total_processed, 'created': run.total_created, 'updated': run.total_updated, 'failed_pages': run.total_failed_pages, 'error': run.error_message})"
```

### Expected behavior

- `opportunities.collect_opportunities` dispatches `opportunities.collect_source`.
- Worker logs show a source dispatch event, source task start, source task end, and run stats.
- A `PipelineRun` row is created with source, status, duration, processed, created, updated, and failed pages.
- If raw `NEW` records exist, `opportunities.materialize_opportunities` is scheduled.
- When raw backlog is drained, `opportunities.generate_embeddings` is scheduled if canonical rows are missing vectors.

### What to show on dashboard

- `Pipeline Health` latest processed, created, updated, duration, and status.
- `Celery Monitoring` workers, active tasks, scheduled tasks, queue length.
- `Source Monitoring` row for the executed source.
- `Pipeline Lag` while raw records are pending.
- `AI Readiness` after embedding generation.

### What to explain orally

Beat only dispatches the top-level task. The top-level task checks due sources and dispatches one task per source. The source task owns locking and `PipelineRun`. Downstream tasks are event-driven: materialization starts only when raw records exist, and embeddings start only when materialization has drained the raw backlog.

## 4. Monitoring anomaly detection test

Purpose: prove that the monitoring layer can detect a stuck pipeline run without needing a real scraper failure.

### Command

Create a synthetic stuck run and read anomalies:

```bash
docker compose exec backend python manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from opportunities.models import PipelineRun, PipelineRunStatus; from opportunities.monitoring import collect_pipeline_anomalies; PipelineRun.objects.create(source='keejob', status=PipelineRunStatus.RUNNING, started_at=timezone.now()-timedelta(hours=3)); print(collect_pipeline_anomalies())"
```

### Expected behavior

- Output contains a `CRITICAL` anomaly.
- The anomaly title is `Pipeline source run stuck`.
- The issue key follows `source:keejob:stuck`.

### What to show on dashboard

- `Active Alerts` shows a critical stuck-run alert if auto-recovery has not already cleared it.
- `Source Monitoring` still shows source history and recent failure state.

### What to explain orally

Monitoring is not only log-based. It queries persisted `PipelineRun` rows, source freshness, failure streaks, duration thresholds, and embedding backlog. A stuck run is detected by comparing `started_at` against `OPPORTUNITY_PIPELINE_STUCK_SECONDS`.

## 5. Alert triggering test - Discord

Purpose: prove that anomalies become operational alerts with anti-spam state.

### Setup

Set a temporary Discord webhook for the test environment:

```bash
OPPORTUNITY_ALERTS_ENABLED=true
OPPORTUNITY_ALERT_DISCORD_WEBHOOK_URL=<DISCORD_WEBHOOK_URL>
```

Restart the backend or pass the variables to a one-off command. For a defense demo, keep auto-recovery disabled for this specific command so the stuck row remains visible on the dashboard.

### Command

```bash
docker compose run --rm -e OPPORTUNITY_ALERTS_ENABLED=true -e OPPORTUNITY_ALERT_DISCORD_WEBHOOK_URL=<DISCORD_WEBHOOK_URL> -e OPPORTUNITY_AUTO_RECOVERY_ENABLED=false backend python manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from opportunities.models import PipelineRun, PipelineRunStatus; from opportunities.monitoring import evaluate_pipeline_health; PipelineRun.objects.create(source='keejob', status=PipelineRunStatus.RUNNING, started_at=timezone.now()-timedelta(hours=3)); print(evaluate_pipeline_health())"
```

### Expected behavior

- Discord receives a message similar to `[CRITICAL] Pipeline source run stuck`.
- The message includes the source and details.
- The returned health result is `degraded`.
- Re-running the command for the same issue does not spam Discord continuously because alert state stores count, active status, last alert time, cooldown, and TTL.

### What to show on dashboard

- `Active Alerts` shows the critical source alert.
- `Pipeline Health` remains readable even when the pipeline is degraded.
- `Celery Monitoring` is independent from the alert state.

### What to explain orally

Alerting is stateful. `record_issue` does not send a notification for every observation. It increments issue count, applies a threshold, respects cooldown, groups repeated occurrences, and later sends recovery notifications through `record_recovery`.

## 6. Failure scenario - simulate stuck pipeline and lock contention

Purpose: prove that a stuck run plus a held Redis lock blocks duplicate source execution safely instead of launching overlapping scrapers.

### Command

Create a stale `RUNNING` row and an artificial source lock:

```bash
docker compose exec backend python manage.py shell -c "from datetime import timedelta; from django.utils import timezone; from opportunities.models import PipelineRun, PipelineRunStatus; from opportunities.locks import opportunity_pipeline_redis_client, get_pipeline_lock_key; PipelineRun.objects.create(source='keejob', status=PipelineRunStatus.RUNNING, started_at=timezone.now()-timedelta(hours=3)); opportunity_pipeline_redis_client().set(get_pipeline_lock_key('keejob'), 'defense-stuck-lock', ex=3600); print('stuck run and lock created')"
```

Dispatch a source task:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.tasks import collect_source_task; task=collect_source_task.delay('keejob'); print(task.id)"
```

Watch worker logs:

```bash
docker compose logs --tail=80 celery_worker
```

### Expected behavior

- Worker logs show the source task skipped with reason `locked`.
- No overlapping scraper run starts for the same source.
- Monitoring detects the stale `RUNNING` row as stuck.

### What to show on dashboard

- `Active Alerts` shows stuck source if monitor/anomaly detection has run and auto-recovery has not cleared it.
- `Celery Monitoring` may show task activity briefly.
- `Source Monitoring` remains source-specific and does not mix sources.

### What to explain orally

The lock protects external sources and canonical data from concurrent duplicate runs. Lock ownership is token-based, and release is guarded by a Lua script so only the owner can release its lock.

## 7. Recovery scenario - auto-recover a stuck pipeline

Purpose: prove that the system can clear a stuck run and Redis lock without manual database surgery.

### Command

Run the monitor health evaluation with auto-recovery enabled:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.monitoring import evaluate_pipeline_health; print(evaluate_pipeline_health())"
```

Verify the latest stuck run was marked failed:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.models import PipelineRun; run=PipelineRun.objects.order_by('-started_at').first(); print({'source': run.source, 'status': run.status, 'duration': run.duration_seconds, 'error': run.error_message})"
```

Verify the lock was cleared:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.locks import opportunity_pipeline_redis_client, get_pipeline_lock_key; print(opportunity_pipeline_redis_client().get(get_pipeline_lock_key('keejob')))"
```

Optionally dispatch a fresh source run:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.tasks import collect_source_task; task=collect_source_task.delay('keejob', max_pages=1, max_records=5); print(task.id)"
```

### Expected behavior

- `evaluate_pipeline_health` returns `recovered` greater than zero.
- Stale `RUNNING` rows become `failed`.
- Error message is `Auto-recovered after being stuck.`
- Redis source lock returns `None`.
- A new source task can acquire the lock and run.

### What to show on dashboard

- Critical stuck alert disappears after recovery.
- `Pipeline Health` shows no running stuck task.
- `Source Monitoring` shows a failed run with a recovery-related error message.
- A subsequent successful source run demonstrates that recovery unblocked the source.

### What to explain orally

Recovery is automatic and conservative: the monitor marks stale runs failed, records duration, writes an explicit error message, deletes the source lock, and lets normal scheduling dispatch the source again. It does not delete raw or canonical data.

## 8. Embedding and similarity smoke test

Purpose: prove that materialized opportunities can receive vectors and serve similarity results.

### Command

Generate a small embedding batch:

```bash
docker compose run --rm backend python manage.py generate_embeddings --limit 20
```

Check embedding coverage:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.views_admin import get_embedding_monitoring; print(get_embedding_monitoring())"
```

Call a similarity endpoint after selecting an opportunity with an embedding:

```bash
curl -X GET "http://localhost:8000/api/opportunities/<ID>/similar/?k=5"
```

### Expected behavior

- Embedding command reports updated, skipped, and errors.
- Dashboard embedding coverage increases.
- Similar endpoint returns ranked results or an empty list if there are not enough comparable active records.
- If pgvector is disabled or incomplete, similarity falls back to Python vector scoring.

### What to show on dashboard

- `AI Readiness` coverage.
- `pgvector` count if pgvector payloads are populated.
- Similar endpoint response in API client or browser.

### What to explain orally

Embeddings are versioned by model identifier, generated in batches, normalized, and stored both as JSON vectors and optional pgvector payloads. Similarity prefers pgvector when enabled, but has a Python fallback to avoid empty recommendations during backfill.

## 9. API endpoints to verify

Public endpoints:

```bash
curl -X GET http://localhost:8000/api/opportunities/
curl -X GET http://localhost:8000/api/opportunities/<ID>/
curl -X GET "http://localhost:8000/api/opportunities/<ID>/similar/?k=5"
curl -X GET http://localhost:8000/api/sources/
```

Authenticated admin or metrics endpoints:

```bash
curl -X GET http://localhost:8000/api/metrics/pipeline/ -H "Authorization: Bearer <ACCESS_TOKEN>"
curl -X GET http://localhost:8000/api/admin/dashboard/ -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Expected:

- list endpoint returns active opportunities by default
- detail endpoint exposes enrichment fields
- similar endpoint returns ranked, same-type, active candidates when embeddings exist
- sources endpoint is readable
- pipeline metrics and admin dashboard require authentication and authorization

## 10. Recommended automated test suites

Pipeline orchestration tests:

```bash
docker compose run --rm backend python manage.py test opportunities.tests_pipeline_tasks
```

Targeted Sprint 2 suites:

```bash
docker compose run --rm backend python manage.py test tests.tests.RawNormalizationTests
docker compose run --rm backend python manage.py test tests.tests.EmploiTunisieScraperStructuredParsingTests
docker compose run --rm backend python manage.py test tests.tests.OpportunityTextEnrichmentTests
docker compose run --rm backend python manage.py test tests.tests.OpportunityMaterializationTests
docker compose run --rm backend python manage.py test tests.tests.OpportuniteAPITests
docker compose run --rm backend python manage.py test tests.tests.PipelineTests
```

Extended regression suites:

```bash
docker compose run --rm backend python manage.py test tests.test_scrapers
docker compose run --rm backend pytest tests/test_linkedin_scraper.py -q
docker compose run --rm backend python manage.py test tests.tests_quality
docker compose run --rm backend python manage.py test tests.tests_embeddings
docker compose run --rm backend python manage.py test tests.tests_marchespublics
docker compose run --rm backend python manage.py test tests.test_nlp_preprocessing
```

Full backend validation pass:

```bash
docker compose run --rm backend python manage.py test tests.tests tests.test_scrapers tests.tests_quality tests.tests_embeddings tests.tests_marchespublics tests.test_nlp_preprocessing opportunities.tests_pipeline_tasks
docker compose run --rm backend pytest tests/test_linkedin_scraper.py -q
```

## 11. Data quality spot checks

EmploiTunisie source URL completeness:

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); print({'null': qs.filter(source_item_url__isnull=True).count(), 'empty': qs.filter(source_item_url='').count()})"
```

Critical field coverage:

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); print({'organisation_empty': qs.filter(organisation_nom='').count(), 'ville_empty': qs.filter(ville='').count(), 'contract_empty': qs.filter(contract_type='').count(), 'description_html_empty': qs.filter(description_html='').count()})"
```

Structured experience and skills coverage:

```bash
docker compose run --rm backend python manage.py shell -c "from django.db.models import Q; from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); total=qs.count(); exp=qs.filter(Q(experience_min__isnull=False) | Q(experience_max__isnull=False)).count(); skills=qs.exclude(skills=[]).count(); print({'total': total, 'with_experience_bounds': exp, 'with_skills': skills})"
```

Pipeline run health:

```bash
docker compose exec backend python manage.py shell -c "from opportunities.views_admin import get_pipeline_stats, get_source_monitoring, get_pipeline_lag_monitoring; print(get_pipeline_stats()); print(get_source_monitoring()); print(get_pipeline_lag_monitoring())"
```

## 12. Release sign-off checklist

Sprint 2 is ready for release when:

- Docker services start cleanly
- `celery_worker` and `celery_beat` are running
- manual CLI collection works for at least one source
- Celery forced dispatch creates a `PipelineRun`
- materialization drains raw `NEW` backlog
- embedding coverage is progressing or intentionally deferred
- monitoring detects a synthetic stuck run
- auto-recovery clears the synthetic stuck run and Redis lock
- Discord alerting is verified in a safe test channel, if enabled for production
- dashboard shows KPIs, active alerts, source monitoring, Celery status, lag, and embedding readiness
- targeted Sprint 2 tests pass
- public API and similar endpoint respond correctly

## 13. Key talking points for presentation

- Sprint 2 delivered an ingestion subsystem, not only scrapers.
- CLI and Celery share the same source registry and collection core.
- Production execution is asynchronous, source-scoped, locked, observable, and retry-aware.
- Scheduling is intelligent: due, stale, retry-after-failure, running, and running-stale are explicit states.
- Raw data is retained before canonical materialization, so parsing rules can be replayed without scraping again.
- Materialization is idempotent and uses conservative merge rules to avoid destroying better existing data.
- Monitoring is database-backed and detects stuck runs, stale sources, repeated failures, duration anomalies, and embedding backlog.
- Alerts are stateful: threshold, cooldown, grouping, Discord delivery, and recovery notification.
- Recovery is automatic: stale `RUNNING` rows are marked failed and their Redis locks are cleared.
- The dashboard is an operator view over the pipeline, worker state, lag, embedding readiness, and alerts.
