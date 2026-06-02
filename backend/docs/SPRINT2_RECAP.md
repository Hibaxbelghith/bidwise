# Sprint 2 - Technical recap

Last updated: 2026-05-05

## Verdict

Sprint 2 is complete for the opportunities pipeline scope.

The implementation is no longer a simple scraper command. It is now a production-oriented ingestion architecture with a scheduler/orchestration core, manual CLI entry point, Celery workers, Celery Beat scheduling, Redis-backed locks, operational monitoring, anomaly detection, Discord alerting, automatic recovery, raw replay safety, canonical materialization, API exposure, embeddings, and similarity search.

The original Sprint 2 target was the backend data layer behind opportunity discovery. That scope is implemented end to end: collection, raw persistence, normalization, enrichment, quality scoring, materialization, API exposure, embedding generation, and similarity.

## Executive value for demo

These are the strongest Sprint 2 talking points for a technical presentation:

- Pipeline: we built a complete, automated, idempotent data pipeline that can collect, persist, normalize, enrich, quality-check, materialize, embed, and expose opportunities without manual intervention.
- Celery: heavy work is externalized to Celery so the API remains fast, responsive, and scalable while scraping, materialization, embeddings, and monitoring run asynchronously.
- Monitoring: the system is self-monitored with anomaly detection, structured events, source freshness tracking, failed-run detection, Discord alerting, and automatic stuck-run recovery.
- AI: vector embeddings power semantic similarity today and create the foundation for a future recommendation engine.
- Quality: data quality is measured and enforced with validation, quality scoring, explicit rejection states, default image handling, and API-level quality metrics.

## Scope delivered

| Goal | State | Evidence in code |
| --- | --- | --- |
| Scraping stability | Complete | `opportunities/scraping/pipeline.py`, `opportunities/scraping/sources/*`, scraper regression tests |
| Scheduler/orchestration core | Complete | `opportunities/pipeline.py`, `opportunities/management/commands/collect_opportunities.py` |
| Async execution | Complete | `opportunities/tasks.py`, `backend/config/celery.py`, `docker-compose.yml` |
| Scheduled execution | Complete | `CELERY_BEAT_SCHEDULE` in `backend/config/settings.py`, `celery_beat` service |
| Intelligent scheduling | Complete | `get_source_schedule_state`, `get_due_sources`, `select_sources_for_pipeline` |
| Raw shadow storage | Complete | `RawOpportunite`, raw identity constraints, payload hash, content fingerprint |
| Normalization | Complete | `opportunities/normalization/service.py` |
| Enrichment and NLP layer | Complete | `opportunities/enrichment/text_enrichment.py`, `opportunities/nlp/extraction.py`, `opportunities/nlp/skills.py` |
| Quality gate | Complete | `opportunities/quality/quality_gate.py`, `opportunities/scoring/quality.py` |
| Materialization | Complete | `opportunities/materialization/service.py`, `opportunities/processing.py` |
| API | Complete | `opportunities/views.py`, `opportunities/filters.py`, `opportunities/serializers.py` |
| Embeddings | Complete | `opportunities/embeddings/service.py`, `generate_embeddings`, `opportunities.generate_embeddings` |
| Similarity | Complete | `opportunities/similarity.py`, similar endpoint with Python and pgvector fallback |
| Monitoring | Complete | `opportunities/monitoring.py`, `opportunities/views_admin.py` |
| Data quality metrics | Complete | `opportunities/dataset_metrics.py`, `/api/metrics/pipeline/` |
| Image consistency | Complete | default logo validation in normalization, materialization, and serializers |
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

The source registry and aliases live in the scheduler/orchestrator module, `opportunities/pipeline.py`. Runtime source order comes from `OPPORTUNITY_PIPELINE_SOURCES`, then `OPPORTUNITY_SOURCE_CONFIG.priority`.

## Actual pipeline path

Production data path:

```text
Celery Beat or CLI
  -> scheduler/orchestrator (`opportunities/pipeline.py`)
  -> source scraper
  -> run_collection
  -> RawOpportunite
  -> materialization task or manual processing (`opportunities/processing.py`)
  -> normalize_raw_opportunity
  -> enrich_opportunity_text (delegates to NLP extraction helpers)
  -> evaluate_opportunity
  -> materialize_opportunity
  -> Opportunite
  -> embedding generation
  -> similarity/API/admin dashboard/metrics
```

Role boundaries in the raw-to-canonical step:

- Normalization maps raw source payloads into canonical structured fields. It owns source schema mapping, date parsing, canonical type/status values, city/company cleanup, URL canonicalization, and structured experience parsing.
- Enrichment does not remap source schemas and no longer owns direct NLP extraction logic. It orchestrates structured normalized values with NLP-derived output, preserves fallback rules, and returns stable fields such as salary, skills, language fallback, and experience fallback from description text only when no structured experience is present.
- The NLP layer owns reusable text extraction helpers and the canonical skill keyword list. It does not schedule sources, persist raw data, score quality, or materialize canonical rows.
- Scoring evaluates the normalized and enriched payload quality; it does not extract new business fields.
- Materialization persists the final payload to `Opportunite`, applies DB safety checks, deduplication, merge rules, and status policy.

Important distinction:

- `opportunities/pipeline.py` is the source collection scheduler/orchestrator. It selects due sources, applies adaptive scheduling rules, constructs scrapers, and records collection results; it is not the raw-to-canonical business data pipeline.
- `opportunities/processing.py` is the real data pipeline for one raw opportunity or a raw batch. It runs normalization, enrichment orchestration, quality scoring, materialization, raw state transitions, and optional inline embeddings.
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
- `opportunities/nlp/extraction.py`
- `opportunities/nlp/skills.py`
- `opportunities/quality/quality_gate.py`
- `opportunities/materialization/service.py`
- `opportunities/embeddings/service.py`
- `opportunities/similarity.py`
- `opportunities/views.py`
- `opportunities/views_admin.py`
- `opportunities/dataset_metrics.py`
- `frontend/src/features/admin/DashboardAdminPage.jsx`

## NLP Layer

The NLP layer is separate from enrichment so extraction behavior can evolve without changing pipeline orchestration.

- `opportunities/nlp/extraction.py` owns reusable extraction helpers for salary, hard skills, soft skills, and language detection.
- `opportunities/nlp/skills.py` owns the canonical skill keyword list used by extraction.
- `opportunities/enrichment/text_enrichment.py` consumes NLP extraction, merges it with normalized structured fields, and returns the stable enrichment contract expected by `processing.py`.
- NLP extraction has no source scheduling, raw persistence, quality scoring, materialization, embedding, or API responsibility.

## Execution architecture

### Manual CLI

The command `python manage.py collect_opportunities` is a direct operational entry point for collection.

It supports:

- all configured sources, ordered by priority
- single-source execution with `--source`
- scheduler-aware execution with `--respect-schedule`
- source-specific controls such as `--max-pages`, `--max-records`, `--keyword`, `--location`, `--timeout`, `--min-delay`, `--max-delay`, `--stage-only`, and `--fetch-details`

The command delegates to `run_opportunity_pipeline` in `opportunities/pipeline.py`, the same scheduler/orchestrator used by Celery for source registry lookup, source-key normalization, source priority, scraper construction, and scheduling decisions.

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

### Celery queues and LLM opportunity enrichment

The scraping pipeline and the LLM enrichment backfill are intentionally isolated in separate Celery queues.

```text
celery_worker
  queue: celery
  role: scraping dispatch, source collection, raw materialization, embeddings, monitoring

celery_enrichment
  queue: opportunity_enrichment
  role: slow offline LLM backfill for opportunity skills and job metadata

celery_profile
  queue: profile_resume
  role: resume parsing and profile embedding tasks
```

Why this matters:

- Local LLM/Ollama calls can be slow and unpredictable.
- Scraping must stay responsive even when LLM enrichment is running.
- The enrichment worker uses `--concurrency=1` and `--prefetch-multiplier=1` so one slow local model call does not reserve a large backlog.
- `CELERY_TASK_ROUTES` sends `ai.enrich_opportunity_llm_backfill` and `ai.enrich_opportunity_with_llm` to `opportunity_enrichment`, not to the default scraping queue.

The periodic LLM backfill is configured through:

- `OPPORTUNITY_LLM_BACKFILL_ENABLED`
- `OPPORTUNITY_LLM_BACKFILL_SOURCE`
- `OPPORTUNITY_LLM_BACKFILL_LIMIT`
- `OPPORTUNITY_LLM_BACKFILL_MIN_DESCRIPTION_CHARS`
- `OPPORTUNITY_LLM_BACKFILL_DELAY_SECONDS`
- `OPPORTUNITY_LLM_BACKFILL_WORKERS`
- `OPPORTUNITY_LLM_BACKFILL_LOCK_SECONDS`
- `OPPORTUNITY_LLM_BACKFILL_CRON_MINUTE`

The backfill command name is still `enrich_opportunities_with_gemini` for backward compatibility, but the runtime provider can be local Ollama. The task runs only as an offline batch; recommendations do not call the LLM at request time.

Candidate selection is guarded:

- only active job opportunities are selected;
- non-job sources such as `MarchesPublics` are excluded;
- already rich skill sets are skipped unless force mode is used;
- weak or generic skill lists from rich descriptions are eligible for LLM cleanup;
- a Redis cache lock prevents overlapping LLM backfill runs.

### Celery Beat

`CELERY_BEAT_SCHEDULE` dispatches two pipeline jobs every 15 minutes:

- `opportunities.collect_opportunities`
- `opportunities.monitor_pipeline`

It can also dispatch the offline LLM backfill on a separate cadence:

- `ai.enrich_opportunity_llm_backfill`

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
| `opportunities/pipeline.py` | Source scheduler/orchestrator: source registry, aliases, priority, source config, adaptive scheduler state, scraper construction, collection result building | Called by the CLI command and Celery dispatch to choose due sources and launch collection; not used for raw-to-canonical processing | due/stale/retry/running-stale decisions, EMA-smoothed metrics, adaptive score, hard failure cooldown, source priority ordering, source aliases, stale running cleanup before synchronous relaunch, fallback when no source is due |
| `opportunities/tasks.py` | Production Celery orchestration | Beat calls `collect_opportunities_pipeline`; it dispatches `collect_source_task`; source task schedules materialization; materialization schedules embeddings; monitor task evaluates health | Redis locks, `PipelineRun` persistence, retry after source exception, failed-page threshold, bounded batches, self-requeue, no-progress embedding alert, DB connection cleanup |
| `ai/tasks.py` | Asynchronous AI maintenance tasks | Runs profile skill storage tasks and the offline opportunity LLM backfill through the `opportunity_enrichment` queue | Redis cache lock, configurable batch size, minimum description length guard, DB connection cleanup, no request-time LLM calls |
| `ai/management/commands/enrich_opportunities_with_gemini.py` | Offline opportunity enrichment command | Called manually or by `ai.enrich_opportunity_llm_backfill`; provider can be local Ollama despite the legacy command name | active job-only selection, non-job source exclusion, weak/generic skill detection, dry-run audit mode, configurable delay and workers |
| `opportunities/monitoring.py` | Observability, anomaly detection, alerting, recovery | Called by source observation, monitor task, and admin dashboard | structured logs, Redis/cache alert state, Discord alerts, threshold/cooldown anti-spam, recovery notifications, stuck-run detection, failed-streak detection, duration anomalies, embedding backlog detection, automatic stuck recovery |
| `opportunities/scraping/pipeline.py` | Raw ingestion boundary | Called by `run_source_collection` after a scraper yields records | shadow storage, source upsert, URL and record-id identity, payload hash, content fingerprint, requeue on impactful raw changes, max empty pages, max failed pages, page-level stats |
| `opportunities/scraping/sources/*` | Source-specific adapters for Keejob, EmploiTunisie, LinkedIn, MarchesPublics | Each scraper returns raw records or raw pages to the shared scraping pipeline | HTTP retry adapters, random request delays, pagination caps, max records, duplicate skipping, 403 block detection, detail-page enrichment, listing fallback for MarchesPublics, fail-safe LinkedIn scraper, structured field extraction |
| `opportunities/normalization/service.py` | Canonical mapping from raw payload to normalized dict | Called first by `process_raw_opportunity` | deterministic field mapping, date/type/status parsing, source URL canonicalization, structured field cleanup, structured experience bounds |
| `opportunities/enrichment/text_enrichment.py` | Enrichment orchestration that merges normalized structured values with NLP-derived fields | Called by `process_raw_opportunity` after normalization and before quality scoring; delegates reusable extraction to `opportunities/nlp/extraction.py` | stable enrichment contract, structured skill merge, salary resolution, language fallback, description-only experience fallback, safe default output on parser failure |
| `opportunities/nlp/extraction.py` | Reusable NLP extraction helpers for enrichment | Called by `opportunities/enrichment/text_enrichment.py` | salary extraction, hard skill detection, soft skill detection, language detection, normalized token matching |
| `opportunities/nlp/skills.py` | Canonical skill keyword registry | Imported by NLP extraction and kept as a stable skill vocabulary surface | centralized skill list, consistent matching vocabulary, legacy import compatibility through enrichment |
| `opportunities/quality/quality_gate.py` | Quality scoring and usability gate | Called after enrichment | quality score, quality tier, recommendation readiness, minimum title/description/source URL checks |
| `opportunities/materialization/service.py` | Canonical persistence for `Opportunite` | Called by `process_raw_opportunity` after normalization, enrichment, and quality gate | transactional deduplication, source+URL identity, external-id fallback, required-field validation, choice validation, URL quality policy, quality score persistence, non-destructive merge rules, status correction, previous duplicate archiving |
| `opportunities/processing.py` | Real raw-to-canonical data pipeline and batch processor | Called by manual shell tests and `materialize_opportunities_task`; `process_raw_opportunity` runs normalization, enrichment orchestration, scoring, and materialization in order | per-record isolation, row locks, rejection without deleting raw data, replay-safe state transitions, optional inline embeddings, deterministic batch order |
| `opportunities/embeddings/service.py` | Embedding model abstraction | Called by `generate_embeddings` command and optional inline processing | model whitelist, model versioning, cached CPU model, batch encoding, L2-normalized vectors, text preprocessing |
| `opportunities/dataset_metrics.py` | Lightweight operational and data quality metrics | Called by `/api/metrics/pipeline/` and admin dashboard enrichment | raw processing distribution, last-run summary, pipeline flow, description/salary/skills/embedding coverage, source reliability, throughput, freshness delay |
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
- data quality percentages for description, salary, skills, and embeddings
- source reliability score based on success, errors, and freshness
- latest pipeline throughput in processed records per minute
- freshness delay between scraping and availability

The public authenticated pipeline metrics endpoint, `GET /api/metrics/pipeline/`, also exposes a lightweight flow summary:

```text
Scraping -> Processing -> Materialization -> Embeddings
```

It includes:

- `last_run_processed`
- `last_run_created`
- `last_run_updated`
- `last_run_duration`
- `last_run_status`
- `data_quality`
- `source_reliability_score`
- `pipeline_throughput`
- `freshness_delay`

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
- Image consistency layer: missing or invalid company images are normalized to a default placeholder, and Keejob similar-offer logos are not reused as company logos.
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
- `tests.tests_pipeline_tasks`

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
- data quality percentages and pipeline flow metrics
- explicit default image handling to prevent cross-company logo leakage
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
