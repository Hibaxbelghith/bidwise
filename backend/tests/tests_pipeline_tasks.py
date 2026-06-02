from datetime import timedelta
from unittest.mock import call, patch

from django.core.cache import cache
from django.utils import timezone
from django.test import SimpleTestCase, TestCase, override_settings

from ai.tasks import enrich_opportunity_llm_backfill_task
from opportunities.management.commands.collect_opportunities import (
    collect_opportunities_pipeline,
    normalize_source,
)
from opportunities.models import PipelineRun, PipelineRunStatus, SourceSchedulerState
from opportunities.pipeline import (
    build_collection_result,
    compute_adaptive_interval,
    get_configured_sources,
    get_source_schedule_state,
    run_opportunity_pipeline,
)
from opportunities.services.scheduler_monitoring import scheduler_decision_cache_key
from opportunities.tasks import (
    collect_opportunities_pipeline as collect_opportunities_task,
    collect_source_task,
    generate_embeddings_task,
    materialize_opportunities_task,
)


class PipelineSourceOrderingTests(SimpleTestCase):
    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=[
            "keejob",
            "linkedin",
            "emploi_tn",
            "marches_publics",
        ],
        OPPORTUNITY_SOURCE_CONFIG={
            "linkedin": {"priority": 1},
            "keejob": {"priority": 2},
            "emploi_tn": {"priority": 3},
            "marches_publics": {"priority": 4},
        },
    )
    def test_configured_sources_are_ordered_by_priority(self):
        self.assertEqual(
            get_configured_sources(),
            ["linkedin", "keejob", "emploi_tn", "marches_publics"],
        )

    @patch("opportunities.management.commands.collect_opportunities.run_opportunity_pipeline")
    def test_cli_pipeline_uses_core_pipeline(self, run_pipeline_mock):
        run_pipeline_mock.return_value = []

        result = collect_opportunities_pipeline()

        self.assertEqual(result, [])
        run_pipeline_mock.assert_called_once()


class PipelineDispatchTests(TestCase):
    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=[
            "keejob",
            "linkedin",
            "emploi_tn",
            "marches_publics",
        ],
        OPPORTUNITY_SOURCE_CONFIG={
            "linkedin": {"priority": 1},
            "keejob": {"priority": 2},
            "emploi_tn": {"priority": 3},
            "marches_publics": {"priority": 4},
        },
    )
    @patch("opportunities.tasks.collect_source_task.apply_async")
    def test_celery_dispatches_due_sources_by_priority(self, apply_async_mock):
        cache.clear()

        result = collect_opportunities_task.run(force=True)

        self.assertEqual(
            result["sources"],
            ["linkedin", "keejob", "emploi_tn", "marches_publics"],
        )
        apply_async_mock.assert_has_calls(
            [
                call(args=["linkedin"], kwargs={}),
                call(args=["keejob"], kwargs={}),
                call(args=["emploi_tn"], kwargs={}),
                call(args=["marches_publics"], kwargs={}),
            ]
        )
        self.assertEqual(apply_async_mock.call_count, 4)
        self.assertEqual(
            cache.get(scheduler_decision_cache_key("linkedin"))["source"],
            "linkedin",
        )

    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=[
            "keejob",
            "linkedin",
            "emploi_tn",
            "marches_publics",
        ],
        OPPORTUNITY_SOURCE_CONFIG={
            "linkedin": {"priority": 1},
            "keejob": {"priority": 2},
            "emploi_tn": {"priority": 3},
            "marches_publics": {"priority": 4},
        },
        OPPORTUNITY_SCHEDULER_MAX_SOURCES_PER_TICK=2,
    )
    @patch("opportunities.tasks.collect_source_task.apply_async")
    def test_celery_dispatch_respects_max_sources_per_tick(self, apply_async_mock):
        result = collect_opportunities_task.run(force=True)

        self.assertEqual(result["sources"], ["linkedin", "keejob"])
        self.assertEqual(
            [item["source"] for item in result["skipped_sources"]],
            ["emploi_tn", "marches_publics"],
        )
        apply_async_mock.assert_has_calls(
            [
                call(args=["linkedin"], kwargs={}),
                call(args=["keejob"], kwargs={}),
            ]
        )
        self.assertEqual(apply_async_mock.call_count, 2)

    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=["keejob"],
        OPPORTUNITY_SOURCE_CONFIG={"keejob": {"priority": 1}},
        OPPORTUNITY_SCHEDULER_DISPATCH_DEDUP_SECONDS=5 * 60,
    )
    @patch("opportunities.tasks.collect_source_task.apply_async")
    def test_celery_dispatch_skips_recently_dispatched_source(self, apply_async_mock):
        SourceSchedulerState.objects.create(
            source="keejob",
            last_dispatched_at=timezone.now() - timedelta(seconds=30),
        )

        result = collect_opportunities_task.run(force=True)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["skipped_sources"], [{"source": "keejob", "reason": "recently_dispatched"}])
        apply_async_mock.assert_not_called()


class OpportunityLLMBackfillTaskTests(TestCase):
    @override_settings(OPPORTUNITY_LLM_BACKFILL_ENABLED=False)
    def test_llm_backfill_skips_when_disabled(self):
        self.assertEqual(
            enrich_opportunity_llm_backfill_task.run(),
            {"status": "skipped", "reason": "disabled"},
        )

    @override_settings(
        OPPORTUNITY_LLM_BACKFILL_ENABLED=True,
        OPPORTUNITY_LLM_BACKFILL_SOURCE="LinkedIn",
        OPPORTUNITY_LLM_BACKFILL_LIMIT=7,
        OPPORTUNITY_LLM_BACKFILL_MIN_DESCRIPTION_CHARS=1200,
        OPPORTUNITY_LLM_BACKFILL_DELAY_SECONDS=0,
        OPPORTUNITY_LLM_BACKFILL_WORKERS=1,
    )
    @patch("ai.tasks.call_command")
    def test_llm_backfill_calls_enrichment_command_with_guarded_scope(self, call_command_mock):
        cache.clear()

        result = enrich_opportunity_llm_backfill_task.run()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["source"], "LinkedIn")
        self.assertEqual(result["limit"], 7)
        call_command_mock.assert_called_once_with(
            "enrich_opportunities_with_gemini",
            source="LinkedIn",
            weak_skills_only=True,
            min_description_chars=1200,
            limit=7,
            delay_seconds=0.0,
            workers=1,
        )

    @override_settings(
        OPPORTUNITY_LLM_BACKFILL_ENABLED=True,
        OPPORTUNITY_LLM_BACKFILL_LOCK_SECONDS=60,
    )
    @patch("ai.tasks.call_command")
    def test_llm_backfill_skips_when_locked(self, call_command_mock):
        cache.clear()
        cache.add("ai:opportunity_llm_backfill:lock", "locked", timeout=60)

        self.assertEqual(
            enrich_opportunity_llm_backfill_task.run(),
            {"status": "skipped", "reason": "locked"},
        )
        call_command_mock.assert_not_called()


class PipelineCoreExecutionTests(TestCase):
    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=["keejob"],
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
            },
        },
    )
    @patch("opportunities.pipeline.run_source_collection")
    def test_respect_schedule_skips_when_no_sources_are_due(self, run_source_mock):
        finished_at = timezone.now()
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_created=1,
            created_count=1,
        )
        run_source_mock.return_value = {
            "source": "keejob",
            "stats": {
                "created": 0,
                "updated": 1,
                "skipped": 0,
                "failed_pages": 0,
                "errors": [],
            },
        }

        results = run_opportunity_pipeline(respect_schedule=True)

        self.assertEqual(results, [])
        run_source_mock.assert_not_called()

    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=["keejob"],
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
            },
        },
    )
    @patch("opportunities.pipeline.run_source_collection")
    def test_schedule_bypass_still_writes_scheduler_decision_cache(self, run_source_mock):
        cache.clear()
        run_source_mock.return_value = {
            "source": "keejob",
            "stats": {
                "created": 1,
                "updated": 0,
                "skipped": 0,
                "failed_pages": 0,
                "errors": [],
            },
        }

        results = run_opportunity_pipeline(respect_schedule=False)

        self.assertEqual([result["source"] for result in results], ["keejob"])
        cached = cache.get(scheduler_decision_cache_key("keejob"))
        self.assertIsNotNone(cached)
        self.assertEqual(cached["source"], "keejob")
        self.assertIn("score", cached["metrics"])

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
            },
        },
    )
    def test_schedule_freshness_counts_updated_records(self):
        finished_at = timezone.now()
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_processed=1,
            total_updated=1,
            updated_count=1,
        )

        state = get_source_schedule_state("keejob")

        self.assertFalse(state["is_stale"])
        self.assertEqual(state["last_activity_at"], finished_at)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_ema_alpha": 0.5,
            },
        },
    )
    def test_schedule_metrics_use_ema_for_volume_and_failures(self):
        now_value = timezone.now()
        activity_at = now_value - timedelta(minutes=40)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=activity_at,
            finished_at=activity_at,
            total_processed=10,
            total_created=10,
            created_count=10,
        )
        failed_at = now_value - timedelta(minutes=30)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.FAILED,
            started_at=failed_at,
            finished_at=failed_at,
            total_failed_pages=1,
        )
        latest_at = now_value - timedelta(minutes=20)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=latest_at,
            finished_at=latest_at,
            total_processed=2,
            total_created=2,
            created_count=2,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertAlmostEqual(state["schedule_metrics"]["recent_created_avg"], 6.0)
        self.assertAlmostEqual(state["schedule_metrics"]["recent_created_mean"], 6.0)
        self.assertAlmostEqual(state["schedule_metrics"]["failure_rate"], 0.25)
        self.assertAlmostEqual(state["schedule_metrics"]["failure_rate_mean"], 1 / 3)
        self.assertIn("adaptive_score", state["schedule_metrics"])

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_schedule_seconds": 30 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_high_created_avg": 5,
            },
        },
    )
    def test_adaptive_schedule_runs_high_created_volume_sooner(self):
        now_value = timezone.now()
        finished_at = now_value - timedelta(minutes=40)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_processed=8,
            total_created=8,
            created_count=8,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertEqual(state["base_interval_seconds"], 60 * 60)
        self.assertEqual(state["interval_seconds"], 30 * 60)
        self.assertEqual(state["reason"], "adaptive_high_created_volume")
        self.assertIn("high_created_volume_speedup", state["adaptive_rules"])
        self.assertEqual(state["schedule_metrics"]["recent_created_avg"], 8)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_high_created_avg": 10,
                "adaptive_high_updated_avg": 10,
                "adaptive_score_speedup_threshold": 0.5,
            },
        },
    )
    def test_adaptive_schedule_uses_score_when_no_existing_rule_matches(self):
        now_value = timezone.now()
        finished_at = now_value - timedelta(minutes=50)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_processed=6,
            total_created=6,
            created_count=6,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertEqual(state["interval_seconds"], 45 * 60)
        self.assertEqual(state["reason"], "adaptive_score_high_activity")
        self.assertIn("score_high_activity_speedup", state["adaptive_rules"])
        self.assertAlmostEqual(state["schedule_metrics"]["adaptive_score"], 0.6)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_schedule_seconds": 30 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_high_updated_avg": 6,
            },
        },
    )
    def test_adaptive_schedule_runs_high_updated_volume_sooner(self):
        now_value = timezone.now()
        finished_at = now_value - timedelta(minutes=50)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_processed=8,
            total_created=0,
            total_updated=8,
            updated_count=8,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertFalse(state["is_stale"])
        self.assertEqual(state["interval_seconds"], 45 * 60)
        self.assertEqual(state["reason"], "adaptive_high_updated_volume")
        self.assertIn("high_updated_volume_speedup", state["adaptive_rules"])
        self.assertEqual(state["schedule_metrics"]["recent_updated_avg"], 8)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 8 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_high_created_avg": 5,
            },
        },
    )
    def test_adaptive_schedule_enforces_min_interval(self):
        now_value = timezone.now()
        finished_at = now_value - timedelta(minutes=6)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=finished_at,
            finished_at=finished_at,
            total_processed=8,
            total_created=8,
            created_count=8,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertEqual(state["interval_seconds"], 5 * 60)
        self.assertEqual(state["reason"], "adaptive_high_created_volume")

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 6 * 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_zero_runs_threshold": 3,
            },
        },
    )
    def test_adaptive_schedule_enforces_max_interval(self):
        now_value = timezone.now()
        for hours_ago in (13, 14, 15, 16):
            finished_at = now_value - timedelta(hours=hours_ago)
            PipelineRun.objects.create(
                source="keejob",
                status=PipelineRunStatus.SUCCESS,
                started_at=finished_at,
                finished_at=finished_at,
                total_processed=5,
                total_created=0,
                created_count=0,
            )
        activity_at = now_value - timedelta(hours=17)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=activity_at,
            finished_at=activity_at,
            total_processed=1,
            total_created=1,
            created_count=1,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertFalse(state["is_stale"])
        self.assertEqual(state["interval_seconds"], 12 * 60 * 60)
        self.assertEqual(state["reason"], "adaptive_low_volume")

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_schedule_seconds": 30 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_zero_runs_threshold": 3,
            },
        },
    )
    def test_adaptive_schedule_slows_after_consecutive_zero_created_runs(self):
        now_value = timezone.now()
        for minutes_ago in (75, 120, 180):
            finished_at = now_value - timedelta(minutes=minutes_ago)
            PipelineRun.objects.create(
                source="keejob",
                status=PipelineRunStatus.SUCCESS,
                started_at=finished_at,
                finished_at=finished_at,
                total_processed=5,
                total_created=0,
                created_count=0,
            )
        activity_at = now_value - timedelta(hours=4)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=activity_at,
            finished_at=activity_at,
            total_processed=1,
            total_created=1,
            created_count=1,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertFalse(state["is_due"])
        self.assertFalse(state["is_stale"])
        self.assertEqual(state["base_interval_seconds"], 60 * 60)
        self.assertEqual(state["interval_seconds"], 2 * 60 * 60)
        self.assertEqual(state["reason"], "adaptive_low_volume")
        self.assertEqual(state["schedule_metrics"]["consecutive_zero_runs"], 3)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "failure_retry_seconds": 15 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
            },
        },
    )
    def test_adaptive_schedule_uses_hard_cooldown_when_failure_rate_is_high(self):
        now_value = timezone.now()
        for minutes_ago in (20, 90):
            finished_at = now_value - timedelta(minutes=minutes_ago)
            PipelineRun.objects.create(
                source="keejob",
                status=PipelineRunStatus.FAILED,
                started_at=finished_at,
                finished_at=finished_at,
                total_failed_pages=3,
            )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertFalse(state["is_due"])
        self.assertEqual(state["base_interval_seconds"], 15 * 60)
        self.assertEqual(state["interval_seconds"], 12 * 60 * 60)
        self.assertEqual(state["reason"], "adaptive_hard_failure_cooldown")
        self.assertIn("hard_failure_rate_cooldown", state["adaptive_rules"])
        self.assertEqual(state["schedule_metrics"]["failure_count_recent"], 2)
        self.assertEqual(state["schedule_metrics"]["adaptive_score"], 0.0)

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_failure_threshold": 2,
            },
        },
    )
    def test_adaptive_schedule_backs_off_after_recent_failure_signals(self):
        now_value = timezone.now()
        for minutes_ago, status in (
            (20, PipelineRunStatus.SUCCESS),
            (40, PipelineRunStatus.SUCCESS),
            (60, PipelineRunStatus.SUCCESS),
            (80, PipelineRunStatus.FAILED),
            (100, PipelineRunStatus.FAILED),
        ):
            finished_at = now_value - timedelta(minutes=minutes_ago)
            PipelineRun.objects.create(
                source="keejob",
                status=status,
                started_at=finished_at,
                finished_at=finished_at,
                total_processed=1 if status == PipelineRunStatus.SUCCESS else 0,
                total_created=1 if status == PipelineRunStatus.SUCCESS else 0,
                created_count=1 if status == PipelineRunStatus.SUCCESS else 0,
                total_failed_pages=1 if status == PipelineRunStatus.FAILED else 0,
            )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertFalse(state["is_due"])
        self.assertLessEqual(state["schedule_metrics"]["failure_rate"], 0.5)
        self.assertEqual(state["interval_seconds"], 90 * 60)
        self.assertEqual(state["reason"], "adaptive_recent_failures")
        self.assertIn("recent_failure_signals_backoff", state["adaptive_rules"])

    @override_settings(
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_schedule_seconds": 30 * 60,
                "stale_after_seconds": 12 * 60 * 60,
                "max_duration_seconds": 60,
                "adaptive_zero_runs_threshold": 3,
            },
        },
    )
    def test_stale_sources_stay_prioritized_over_zero_run_slowdown(self):
        now_value = timezone.now()
        for minutes_ago in (40, 90, 140):
            finished_at = now_value - timedelta(minutes=minutes_ago)
            PipelineRun.objects.create(
                source="keejob",
                status=PipelineRunStatus.SUCCESS,
                started_at=finished_at,
                finished_at=finished_at,
                total_processed=5,
                total_created=0,
                created_count=0,
            )
        activity_at = now_value - timedelta(hours=13)
        PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.SUCCESS,
            started_at=activity_at,
            finished_at=activity_at,
            total_processed=1,
            total_created=1,
            created_count=1,
        )

        state = get_source_schedule_state("keejob", now_value=now_value)

        self.assertTrue(state["is_due"])
        self.assertTrue(state["is_stale"])
        self.assertEqual(state["interval_seconds"], 30 * 60)
        self.assertEqual(state["reason"], "stale")
        self.assertIn("stale_priority", state["adaptive_rules"])

    @override_settings(
        OPPORTUNITY_PIPELINE_SOURCES=["keejob"],
        OPPORTUNITY_SOURCE_CONFIG={
            "keejob": {
                "priority": 1,
                "schedule_seconds": 60 * 60,
                "stale_after_seconds": 24 * 60 * 60,
                "max_duration_seconds": 60,
            },
        },
    )
    @patch("opportunities.pipeline.run_source_collection")
    def test_stale_running_run_is_due_and_marked_failed_before_relaunch(self, run_source_mock):
        started_at = timezone.now() - timedelta(minutes=5)
        running_run = PipelineRun.objects.create(
            source="keejob",
            status=PipelineRunStatus.RUNNING,
            started_at=started_at,
        )
        run_source_mock.return_value = {
            "source": "keejob",
            "stats": {
                "created": 1,
                "updated": 0,
                "skipped": 0,
                "failed_pages": 0,
                "errors": [],
            },
        }

        state = get_source_schedule_state("keejob")
        results = run_opportunity_pipeline(respect_schedule=True)

        running_run.refresh_from_db()
        self.assertTrue(state["is_due"])
        self.assertEqual(state["reason"], "running_stale")
        self.assertEqual(running_run.status, PipelineRunStatus.FAILED)
        self.assertIn("max_duration_seconds=60", running_run.error_message)
        self.assertEqual([result["source"] for result in results], ["keejob"])
        run_source_mock.assert_called_once_with("keejob")


class SourceNormalizationTests(SimpleTestCase):
    def test_normalize_source_accepts_legacy_aliases(self):
        self.assertEqual(normalize_source("emploitunisie"), "emploi_tn")
        self.assertEqual(normalize_source("marchespublics"), "marches_publics")


class PipelineMetricsTests(SimpleTestCase):
    def test_update_only_collection_is_not_marked_stale(self):
        now_value = timezone.now()
        result = build_collection_result(
            "keejob",
            {"created": 0, "updated": 2, "skipped": 0, "failed_pages": 0},
            started_at=now_value,
            finished_at=now_value,
        )

        self.assertFalse(result["is_stale"])

    def test_success_rate_counts_created_and_updated_records(self):
        run = PipelineRun(total_processed=4, total_created=1, total_updated=2)

        self.assertEqual(run.success_rate, 0.75)

    @patch("opportunities.pipeline.logger.debug")
    def test_adaptive_interval_logs_structured_scheduler_metrics(self, logger_debug_mock):
        metrics = {
            "recent_created_avg": 0.0,
            "recent_updated_avg": 0.0,
            "failure_rate": 0.0,
            "failure_count_recent": 0,
            "failed_pages_recent": 0,
            "consecutive_zero_runs": 0,
        }

        result = compute_adaptive_interval(
            "keejob",
            {
                "base_interval_seconds": 60 * 60,
                "schedule_seconds": 60 * 60,
                "stale_schedule_seconds": 30 * 60,
                "failure_retry_seconds": 15 * 60,
                "latest_run_status": PipelineRunStatus.SUCCESS,
                "is_stale": False,
                "reason": "scheduled",
            },
            metrics,
        )

        logger_debug_mock.assert_called_once()
        self.assertEqual(logger_debug_mock.call_args.args[0], "scheduler_decision_metrics")
        log_extra = logger_debug_mock.call_args.kwargs["extra"]
        self.assertEqual(log_extra["source"], "keejob")
        self.assertEqual(log_extra["mode"], "adaptive_hybrid")
        self.assertIn("adaptive_raw_score", log_extra)


class SourceTaskTests(SimpleTestCase):
    @patch("opportunities.tasks.record_source_schedule_decision")
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=False)
    def test_collect_source_task_skips_when_locked(
        self,
        acquire_lock_mock,
        redis_client_mock,
        record_source_schedule_decision_mock,
    ):
        result = collect_source_task.run("keejob")

        self.assertEqual(result, {"status": "skipped", "reason": "locked", "source": "keejob"})
        acquire_lock_mock.assert_called_once()
        redis_client_mock.assert_called_once()
        record_source_schedule_decision_mock.assert_called_once_with("keejob")


class MaterializationTaskTests(SimpleTestCase):
    @patch("opportunities.tasks.generate_embeddings_task.apply_async")
    @patch("opportunities.tasks.materialize_opportunities_task.apply_async")
    @patch("opportunities.tasks.Opportunite")
    @patch("opportunities.tasks.RawOpportunite")
    @patch("opportunities.tasks.process_pending_raw_opportunities")
    def test_materialization_task_processes_one_capped_batch(
        self,
        process_pending_mock,
        raw_opportunite_mock,
        opportunite_mock,
        materialize_delay_mock,
        embedding_delay_mock,
    ):
        process_pending_mock.return_value = {
            "processed": 2,
            "created": 1,
            "updated": 1,
            "failed": 0,
        }
        raw_opportunite_mock.objects.filter.return_value.count.return_value = 0
        opportunite_mock.objects.filter.return_value.exists.return_value = False

        result = materialize_opportunities_task.run()

        self.assertEqual(result["processed"], 2)
        process_pending_mock.assert_called_once_with(limit=100)
        raw_opportunite_mock.objects.filter.assert_called_once()
        materialize_delay_mock.assert_not_called()
        embedding_delay_mock.assert_not_called()

    @patch("opportunities.tasks.generate_embeddings_task.apply_async")
    @patch("opportunities.tasks.materialize_opportunities_task.apply_async")
    @patch("opportunities.tasks.Opportunite")
    @patch("opportunities.tasks.RawOpportunite")
    @patch("opportunities.tasks.process_pending_raw_opportunities")
    def test_materialization_task_retriggers_when_new_records_remain(
        self,
        process_pending_mock,
        raw_opportunite_mock,
        opportunite_mock,
        materialize_delay_mock,
        embedding_delay_mock,
    ):
        process_pending_mock.return_value = {
            "processed": 100,
            "created": 100,
            "updated": 0,
            "failed": 0,
        }
        raw_opportunite_mock.objects.filter.return_value.count.return_value = 1

        result = materialize_opportunities_task.run()

        self.assertEqual(result["processed"], 100)
        process_pending_mock.assert_called_once_with(limit=100)
        materialize_delay_mock.assert_called_once_with(countdown=2)
        embedding_delay_mock.assert_not_called()

    @patch("opportunities.tasks.generate_embeddings_task.apply_async")
    @patch("opportunities.tasks.materialize_opportunities_task.apply_async")
    @patch("opportunities.tasks.Opportunite")
    @patch("opportunities.tasks.RawOpportunite")
    @patch("opportunities.tasks.process_pending_raw_opportunities")
    def test_materialization_task_schedules_embeddings_when_raw_is_drained(
        self,
        process_pending_mock,
        raw_opportunite_mock,
        opportunite_mock,
        materialize_delay_mock,
        embedding_delay_mock,
    ):
        process_pending_mock.return_value = {
            "processed": 12,
            "created": 12,
            "updated": 0,
            "failed": 0,
        }
        raw_opportunite_mock.objects.filter.return_value.count.return_value = 0
        opportunite_mock.objects.filter.return_value.exists.return_value = True

        result = materialize_opportunities_task.run()

        self.assertEqual(result["processed"], 12)
        materialize_delay_mock.assert_not_called()
        embedding_delay_mock.assert_called_once_with(countdown=10)


class EmbeddingTaskTests(SimpleTestCase):
    @patch("opportunities.tasks.close_old_connections")
    @patch("opportunities.tasks.release_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=False)
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    def test_embedding_task_skips_when_locked(
        self,
        redis_client_mock,
        acquire_lock_mock,
        release_lock_mock,
        close_old_connections_mock,
    ):
        result = generate_embeddings_task.run()

        self.assertEqual(result, {"status": "skipped", "reason": "locked"})
        acquire_lock_mock.assert_called_once()
        release_lock_mock.assert_not_called()

    @override_settings(OPPORTUNITY_EMBEDDING_TASK_LIMIT=200)
    @patch("opportunities.tasks.close_old_connections")
    @patch("opportunities.tasks.generate_embeddings_task.apply_async")
    @patch("opportunities.tasks.call_command")
    @patch("opportunities.tasks.Opportunite")
    @patch("opportunities.tasks.release_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    def test_embedding_task_processes_one_batch_and_retriggers_if_needed(
        self,
        redis_client_mock,
        acquire_lock_mock,
        release_lock_mock,
        opportunite_mock,
        call_command_mock,
        embedding_delay_mock,
        close_old_connections_mock,
    ):
        missing_queryset = opportunite_mock.objects.filter.return_value
        missing_queryset.count.side_effect = [250, 50]

        result = generate_embeddings_task.run()

        call_command_mock.assert_called_once_with("generate_embeddings", limit=200)
        embedding_delay_mock.assert_called_once_with(countdown=10)
        self.assertEqual(result, {"status": "completed", "processed": 200, "remaining": 50})
        release_lock_mock.assert_called_once()

    @override_settings(OPPORTUNITY_EMBEDDING_TASK_LIMIT=200)
    @patch("opportunities.tasks.close_old_connections")
    @patch("opportunities.tasks.generate_embeddings_task.apply_async")
    @patch("opportunities.tasks.call_command")
    @patch("opportunities.tasks.Opportunite")
    @patch("opportunities.tasks.release_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    def test_embedding_task_does_not_retrigger_when_no_progress_is_made(
        self,
        redis_client_mock,
        acquire_lock_mock,
        release_lock_mock,
        opportunite_mock,
        call_command_mock,
        embedding_delay_mock,
        close_old_connections_mock,
    ):
        missing_queryset = opportunite_mock.objects.filter.return_value
        missing_queryset.count.side_effect = [25, 25]

        result = generate_embeddings_task.run()

        call_command_mock.assert_called_once_with("generate_embeddings", limit=200)
        embedding_delay_mock.assert_not_called()
        self.assertEqual(result, {"status": "completed", "processed": 0, "remaining": 25})
        release_lock_mock.assert_called_once()


class SourceTaskIntegrationTests(TestCase):
    @patch("opportunities.tasks.close_old_connections")
    @patch("opportunities.tasks.RawOpportunite")
    @patch("opportunities.tasks.materialize_opportunities_task.apply_async")
    @patch("opportunities.tasks.release_pipeline_lock", return_value=True)
    @patch("opportunities.tasks.run_source_collection")
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=True)
    def test_collect_source_task_schedules_materialization_after_success(
        self,
        acquire_lock_mock,
        redis_client_mock,
        run_source_collection_mock,
        release_lock_mock,
        materialize_delay_mock,
        raw_opportunite_mock,
        close_old_connections_mock,
    ):
        cache.clear()
        raw_opportunite_mock.objects.filter.return_value.exists.return_value = True
        run_source_collection_mock.return_value = {
            "stats": {
                "created": 1,
                "updated": 0,
                "skipped": 0,
                "failed_pages": 0,
            }
        }

        result = collect_source_task.run("keejob")

        self.assertEqual(result["status"], "completed")
        materialize_delay_mock.assert_called_once_with(countdown=2)
        self.assertEqual(PipelineRun.objects.count(), 1)
        self.assertEqual(PipelineRun.objects.first().status, PipelineRunStatus.SUCCESS)
        self.assertEqual(
            cache.get(scheduler_decision_cache_key("keejob"))["source"],
            "keejob",
        )
        acquire_lock_mock.assert_called_once()
        redis_client_mock.assert_called_once()
        release_lock_mock.assert_called_once()
