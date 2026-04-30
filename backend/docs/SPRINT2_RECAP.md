# Sprint 2 - Technical recap

Last updated: 2026-04-28

## Verdict

Sprint 2 is complete for the opportunities pipeline scope.

The implementation is no longer a simple scraper command. It is now a production-oriented ingestion architecture with a shared pipeline core, manual CLI entry point, Celery workers, Celery Beat scheduling, Redis-backed locks, operational monitoring, anomaly detection, Discord alerting, automatic recovery, raw replay safety, canonical materialization, API exposure, embeddings, and similarity search.

The original Sprint 2 target was the backend data layer behind opportunity discovery. That scope is implemented end to end: collection, raw persistence, normalization, enrichment, quality scoring, materialization, API exposure, embedding generation, and similarity.

## Scope delivered

| Goal | State | Evidence in code |
| --- | --- | --- |
| Scraping stability | Complete | `opportunities/scraping/pipeline.py`, `opportunities/scraping/sources/*`, scraper regression tests |
| Unified pipeline core | Complete | `opportunities/pipeline.py`, `opportunities/management/commands/collect_opportunities.py` |
| Async execution | Complete | `opportunities/tasks.py`, `backend/config/celery.py`, `docker-compose.yml` |
| Scheduled execution | Complete | `CELERY_BEAT_SCHEDULE` in `backend/config/settings.py`, `celery_beat` service |
| Intelligent scheduling | Complete | `get_source_schedule_state`, `get_due_sources`, `select_sources_for_pipeline` |
| Raw shadow storage | Complete | `RawOpportunite`, raw identity constraints, payload hash, content fingerprint |
| Normalization | Complete | `opportunities/normalization/service.py` |
| Enrichment | Complete | `opportunities/enrichment/text_enrichment.py` |
| Quality gate | Complete | `opportunities/quality/quality_gate.py`, `opportunities/scoring/quality.py` |
| Materialization | Complete | `opportunities/materialization/service.py`, `opportunities/processing.py` |
| API | Complete | `opportunities/views.py`, `opportunities/filters.py`, `opportunities/serializers.py` |
| Embeddings | Complete | `opportunities/embeddings/service.py`, `generate_embeddings`, `opportunities.generate_embeddings` |
| Similarity | Complete | `opportunities/similarity.py`, similar endpoint with Python and pgvector fallback |
| Monitoring | Complete | `opportunities/monitoring.py`, `opportunities/views_admin.py` |
| Alerting and recovery | Complete | Discord webhook alerting, Redis alert state, stuck-run recovery |
| Admin dashboard | Complete | `frontend/src/features/admin/DashboardAdminPage.jsx` |

## Active source coverage

Active source registry:

| Source key | Scraper | Priority | Default cadence | Stale cadence | Stale after | Max duration |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `linkedin` | `LinkedInScraper` | 1 | 1 hour | 15 minutes | 12 hours | 10 minutes |
| `keejob` | `KeejobScraper` | 2 | 2 hours | 30 minutes | 12 hours | 20 minutes |
| `emploi_tn` | `EmploiTunisieScraper` | 3 | 6 hours | 1 hour | 24 hours | 20 minutes |
| `marches_publics` | `MarchesPublicsScraper` | 4 | 12 hours | 2 hours | 48 hours | 30 minutes |

Legacy aliases are supported:

- `emploitunisie` maps to `emploi_tn`
- `marchespublics` maps to `marches_publics`

The source registry and aliases live in `opportunities/pipeline.py`. Runtime source order comes from `OPPORTUNITY_PIPELINE_SOURCES`, then `OPPORTUNITY_SOURCE_CONFIG.priority`.

## Actual pipeline path

Production data path:

```text
Celery Beat or CLI
  -> shared pipeline core
  -> source scraper
  -> run_collection
  -> RawOpportunite
  -> materialization task or manual processing
  -> normalize_raw_opportunity
  -> enrich_opportunity_text
  -> evaluate_opportunity
  -> materialize_opportunity
  -> Opportunite
  -> embedding generation
  -> similarity/API/admin dashboard
```

Important distinction:

- CLI execution runs the shared source selection and collection core. It is useful for manual collection and smoke tests.
- Celery execution is the production orchestration path. It creates `PipelineRun` rows, applies per-source locks, retries failures, schedules materialization, schedules embeddings, and feeds monitoring.

Current implementation modules:

- `opportunities/pipeline.py`
- `opportunities/tasks.py`
- `opportunities/monitoring.py`
- `opportunities/scraping/pipeline.py`
- `opportunities/scraping/sources/*`
- `opportunities/processing.py`
- `opportunities/normalization/service.py`
- `opportunities/enrichment/text_enrichment.py`
- `opportunities/quality/quality_gate.py`
- `opportunities/materialization/service.py`
- `opportunities/embeddings/service.py`
- `opportunities/similarity.py`
- `opportunities/views.py`
- `opportunities/views_admin.py`
- `frontend/src/features/admin/DashboardAdminPage.jsx`

## Execution architecture

### Manual CLI

The command `python manage.py collect_opportunities` is a direct operational entry point for collection.

It supports:

- all configured sources, ordered by priority
- single-source execution with `--source`
- scheduler-aware execution with `--respect-schedule`
- source-specific controls such as `--max-pages`, `--max-records`, `--keyword`, `--location`, `--timeout`, `--min-delay`, `--max-delay`, `--stage-only`, and `--fetch-details`

The command delegates to `run_opportunity_pipeline`, which uses the same registry, source normalization, source priority, scraper construction, and scheduling logic used by Celery dispatch.

### Celery worker path

Celery task graph:

```text
opportunities.collect_opportunities
  -> opportunities.collect_source per due source
      -> run_source_collection
      -> PipelineRun finalization
      -> observe_source_run
      -> opportunities.materialize_opportunities when RawOpportunite NEW exists
          -> process_pending_raw_opportunities
          -> re-trigger until NEW backlog is drained
          -> opportunities.generate_embeddings when canonical rows miss vectors
              -> generate_embeddings command in bounded batches
              -> re-trigger while progress continues
```

Key implementation details:

- `collect_opportunities_pipeline` dispatches due sources instead of scraping inline.
- `collect_source_task` owns one source run and records `PipelineRun`.
- `materialize_opportunities_task` processes bounded batches of 100 raw records and requeues itself while backlog remains.
- `generate_embeddings_task` processes a configured limit and requeues itself only if it made progress.
- `monitor_opportunity_pipeline_task` runs health checks and recovery.

### Celery Beat

`CELERY_BEAT_SCHEDULE` dispatches two periodic jobs every 15 minutes:

- `opportunities.collect_opportunities`
- `opportunities.monitor_pipeline`

This makes scheduling external to request handling. The API and frontend read system state; they do not drive scraping.

### Redis

Redis is used for:

- Celery broker
- Celery result backend
- per-source pipeline locks
- embedding lock
- alert state and anti-spam metadata, with Django cache fallback

Locks use owner tokens and a Lua release script so one task cannot accidentally release another task's lock.

## Intelligent scheduling and source orchestration

Scheduling is source-aware, not global.

For each source, `get_source_schedule_state` computes:

- source priority
- latest run
- latest successful run that actually created records
- next allowed run time
- whether the source is due
- whether the source is stale
- whether a running task is stale
- reason code: `scheduled`, `stale`, `retry_after_failure`, `running`, or `running_stale`

Important behaviors:

- A source is stale based on the last successful run that created records, not merely the last completed run.
- Failed sources use `failure_retry_seconds`.
- Stale sources use the shorter `stale_schedule_seconds`.
- A `RUNNING` row older than `max_duration_seconds` becomes due with reason `running_stale`.
- When no source is due and `respect_schedule=True`, the synchronous pipeline falls back to all configured sources as anti-idle protection.
- Celery dispatch uses `get_due_sources`; forced dispatch bypasses the due check.

This design reduces external load while still protecting freshness.

## Module analysis

| Module | Role in pipeline | Execution flow | Advanced features |
| --- | --- | --- | --- |
| `opportunities/pipeline.py` | Shared pipeline core: source registry, aliases, priority, source config, scheduler state, scraper construction, result building | Called by the CLI command and Celery tasks | due/stale/retry/running-stale decisions, source priority ordering, source aliases, stale running cleanup before synchronous relaunch, fallback when no source is due |
| `opportunities/tasks.py` | Production Celery orchestration | Beat calls `collect_opportunities_pipeline`; it dispatches `collect_source_task`; source task schedules materialization; materialization schedules embeddings; monitor task evaluates health | Redis locks, `PipelineRun` persistence, retry after source exception, failed-page threshold, bounded batches, self-requeue, no-progress embedding alert, DB connection cleanup |
| `opportunities/monitoring.py` | Observability, anomaly detection, alerting, recovery | Called by source observation, monitor task, and admin dashboard | structured logs, Redis/cache alert state, Discord alerts, threshold/cooldown anti-spam, recovery notifications, stuck-run detection, failed-streak detection, duration anomalies, embedding backlog detection, automatic stuck recovery |
| `opportunities/scraping/pipeline.py` | Raw ingestion boundary | Called by `run_source_collection` after a scraper yields records | shadow storage, source upsert, URL and record-id identity, payload hash, content fingerprint, requeue on impactful raw changes, max empty pages, max failed pages, page-level stats |
| `opportunities/scraping/sources/*` | Source-specific adapters for Keejob, EmploiTunisie, LinkedIn, MarchesPublics | Each scraper returns raw records or raw pages to the shared scraping pipeline | HTTP retry adapters, random request delays, pagination caps, max records, duplicate skipping, 403 block detection, detail-page enrichment, listing fallback for MarchesPublics, fail-safe LinkedIn scraper, structured field extraction |
| `opportunities/materialization/service.py` | Canonical persistence for `Opportunite` | Called by `process_raw_opportunity` after normalization, enrichment, and quality gate | transactional deduplication, source+URL identity, external-id fallback, required-field validation, choice validation, URL quality policy, quality score persistence, non-destructive merge rules, status correction, previous duplicate archiving |
| `opportunities/processing.py` | Raw-to-canonical batch processor | Called by manual shell tests and `materialize_opportunities_task` | per-record isolation, row locks, rejection without deleting raw data, replay-safe state transitions, optional inline embeddings, deterministic batch order |
| `opportunities/embeddings/service.py` | Embedding model abstraction | Called by `generate_embeddings` command and optional inline processing | model whitelist, model versioning, cached CPU model, batch encoding, L2-normalized vectors, text preprocessing |
| `opportunities/views_admin.py` | Staff-only dashboard API | Frontend calls `/api/admin/dashboard/` | Celery inspect snapshot, KPI aggregation, source monitoring, embedding coverage, raw lag, recent run history, live anomaly list |
| `frontend DashboardAdminPage` | Operator dashboard UI | React page at `/dashboard-admin`, reads `/admin/dashboard/` through the API client | active alert list, Celery health, source monitoring table, embedding readiness, raw backlog, pipeline history, worker unavailable state |

## Monitoring and observability

The monitoring layer tracks both persisted pipeline history and live worker state.

Metrics exposed to the admin dashboard:

- total opportunities
- pipeline activity today
- source count
- write success rate
- latest run status and duration
- total processed, created, updated, failed pages
- per-source runs, failures, average duration, last run, last error
- Celery workers, active tasks, scheduled tasks, reserved tasks, queue length
- raw `NEW` backlog
- embedding coverage
- pgvector coverage
- active anomalies

Anomaly detection includes:

- stuck `RUNNING` pipeline runs older than `OPPORTUNITY_PIPELINE_STUCK_SECONDS`
- no new opportunities for a source beyond its freshness window
- repeated source failures beyond `OPPORTUNITY_ALERT_FAILURE_THRESHOLD`
- scraping duration above source max duration
- embedding backlog above `OPPORTUNITY_EMBEDDING_ALERT_THRESHOLD`
- embedding generation no-progress condition

`evaluate_pipeline_health` records current issues, emits recovery events for resolved issues, auto-recovers stuck runs when enabled, and logs a structured `pipeline_health_check` event.

## Alerting system

Discord alerting is implemented in `opportunities/monitoring.py`.

Alert behavior:

- enabled by `OPPORTUNITY_ALERTS_ENABLED`
- delivered to `OPPORTUNITY_ALERT_DISCORD_WEBHOOK_URL`
- severity levels: `INFO`, `WARNING`, `CRITICAL`
- alert state stored in Redis, with Django cache fallback
- failure threshold controls when repeated issues become active
- cooldown prevents repeated spam for the same issue
- TTL keeps issue state bounded
- repeated occurrences are grouped into the same alert state
- recovery notifications are sent when a previously active issue disappears

Stuck source runs are treated specially: they alert immediately with threshold `1` because they can block a source lock.

## Fault tolerance and resilience

Failure handling exists at several levels:

- HTTP layer: source scrapers use retry adapters for transient 429/5xx failures.
- Scraper layer: failed pages are counted; repeated failures stop the source safely.
- Collection layer: raw records are persisted independently; one bad record increments `skipped` and does not crash the whole source.
- Task layer: `collect_source_task` retries exceptions using the source failure retry interval and configured retry limit.
- Lock layer: source and embedding tasks use Redis locks to avoid concurrent duplicate work.
- Persistence layer: raw records are never deleted during processing; invalid records become `REJECTED` with validation errors.
- Materialization layer: canonical updates are idempotent and transactionally deduplicated.
- Recovery layer: stale `RUNNING` rows are marked `FAILED`, duration is recorded, error message is set, and Redis locks are cleared.

Operational guarantees:

- no intentional raw data loss
- replay-safe normalization and materialization
- partial failure isolation per source and per raw record
- external source load is bounded by cadence, max pages, delays, and early stopping
- duplicate canonical opportunities are constrained by source and item URL
- embeddings can recover from partial batches without overwriting completed work

## Admin dashboard enhancements

The admin dashboard has become an operational console for the pipeline.

Backend endpoint:

- `GET /api/admin/dashboard/`
- staff or superuser only

Frontend page:

- `/dashboard-admin`

Displayed sections:

- KPI cards
- AI readiness and embedding coverage
- raw pipeline lag
- active alerts
- opportunities by source
- pipeline health
- Celery monitoring
- source monitoring

The dashboard is read-only supervision. It does not start scraping; it reflects the state produced by the worker, Beat, database, Redis, and monitoring layer.

## Testing surface

Primary Sprint 2 backend coverage:

- `tests.tests.RawNormalizationTests`
- `tests.tests.EmploiTunisieScraperStructuredParsingTests`
- `tests.tests.OpportunityTextEnrichmentTests`
- `tests.tests.OpportunityMaterializationTests`
- `tests.tests.OpportuniteAPITests`
- `tests.tests.PipelineTests`
- `opportunities.tests_pipeline_tasks`

Extended regression coverage:

- `tests.test_scrapers`
- `tests.test_linkedin_scraper`
- `tests.tests_quality`
- `tests.tests_embeddings`
- `tests.tests_marchespublics`
- `tests.test_nlp_preprocessing`

Important tested behaviors:

- source priority ordering
- CLI delegation to the shared core
- Celery dispatch of due sources
- fallback when no source is due
- stale running run detection
- source aliases
- lock skip behavior
- materialization re-triggering
- embedding lock and re-triggering
- no-progress embedding behavior
- source task integration with `PipelineRun`

## Added value compared to initial scope

The system evolved from a backend data import pipeline into a production-grade data ingestion subsystem.

Key improvements:

- shared core used by CLI and Celery
- asynchronous orchestration
- scheduled source dispatch
- source-specific freshness logic
- source-level locks
- bounded batch processing
- operational monitoring
- Discord alerting
- anti-spam and recovery alerts
- automatic stuck-run recovery
- embedding lifecycle management
- admin dashboard observability

This aligns the Sprint 2 implementation with modern data engineering and DevOps expectations: idempotence, observability, controlled retries, explicit failure states, and replayability.

## Non-blocking backlog

- run a live Docker smoke pass before final release
- review stale failed `PipelineRun` retention and cleanup policy
- expose a manual admin action for safe re-dispatch if needed
- continue duplicate dataset cleanup for old records created before source URL constraints
- Sprint 3 personalization, user actions, and recommendation UX

## Documentation policy

This recap is the single Sprint 2 summary document. The testing guide contains executable defense scenarios and should be kept in sync with this architecture.
