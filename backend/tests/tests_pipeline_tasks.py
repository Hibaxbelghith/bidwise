from datetime import timedelta
from unittest.mock import call, patch

from django.utils import timezone
from django.test import SimpleTestCase, TestCase, override_settings

from opportunities.management.commands.collect_opportunities import (
    collect_opportunities_pipeline,
    normalize_source,
)
from opportunities.models import PipelineRun, PipelineRunStatus
from opportunities.pipeline import (
    get_configured_sources,
    get_source_schedule_state,
    run_opportunity_pipeline,
)
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
    def test_respect_schedule_falls_back_to_all_sources_when_none_are_due(self, run_source_mock):
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

        self.assertEqual([result["source"] for result in results], ["keejob"])
        run_source_mock.assert_called_once_with("keejob")

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


class SourceTaskTests(SimpleTestCase):
    @patch("opportunities.tasks.opportunity_pipeline_redis_client")
    @patch("opportunities.tasks.acquire_pipeline_lock", return_value=False)
    def test_collect_source_task_skips_when_locked(self, acquire_lock_mock, redis_client_mock):
        result = collect_source_task.run("keejob")

        self.assertEqual(result, {"status": "skipped", "reason": "locked", "source": "keejob"})
        acquire_lock_mock.assert_called_once()
        redis_client_mock.assert_called_once()


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
        acquire_lock_mock.assert_called_once()
        redis_client_mock.assert_called_once()
        release_lock_mock.assert_called_once()
