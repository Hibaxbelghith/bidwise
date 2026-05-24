from __future__ import annotations

import json
from io import StringIO
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from ai.recommendation_benchmark.dataset import (
    BenchmarkDataset,
    BenchmarkOpportunity,
    BenchmarkProfile,
    BenchmarkResume,
    ExpectedResult,
    load_benchmark_dataset,
)
from ai.recommendation_benchmark.fixtures import FixtureState
from ai.recommendation_benchmark.fixtures import DjangoBenchmarkFixtureBuilder
from ai.recommendation_benchmark.fixtures import _has_valid_vector_payload
from ai.recommendation_benchmark.metrics import (
    compute_cv_uplift,
    compute_multilingual_robustness,
    compute_semantic_extraction_metrics,
    compute_sparse_profile_robustness,
    metrics_for_recommendations,
)
from ai.recommendation_benchmark.runner import (
    BenchmarkRunOptions,
    RecommendationBenchmarkRunner,
    format_console_report,
)
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


def recommendation(title, *, confidence="MEDIUM", score=0.7, semantic_score=0.7):
    return {
        "id": abs(hash(title)) % 10000,
        "title": title,
        "score": score,
        "match_score": score,
        "semantic_score": semantic_score,
        "business_score": 0.1,
        "recommendation_confidence": confidence,
        "company": "BenchmarkCo",
        "location": "Tunis",
        "type": "EMPLOI",
    }


class RecommendationBenchmarkDatasetTests(SimpleTestCase):
    def test_static_dataset_has_required_profile_and_language_coverage(self):
        dataset = load_benchmark_dataset()

        self.assertGreaterEqual(len(dataset.profiles), 20)
        languages = {profile.language for profile in dataset.profiles}
        self.assertIn("EN", languages)
        self.assertIn("FR", languages)
        self.assertIn("AR", languages)

        categories = {category for profile in dataset.profiles for category in profile.categories}
        for expected_category in (
            "backend",
            "frontend",
            "devops",
            "ai",
            "data",
            "cybersecurity",
            "hr",
            "accounting",
            "marketing",
            "nurse",
            "sparse",
            "cv_only",
            "role_only",
            "multilingual",
        ):
            self.assertIn(expected_category, categories)

        self.assertTrue(any(opportunity.confusing for opportunity in dataset.opportunities))


@override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=384)
class RecommendationBenchmarkFixtureTests(TestCase):
    def test_fixture_update_preserves_existing_llm_enrichment(self):
        source = SourceOpportunite.objects.create(
            nom="BidWise Recommendation Benchmark",
            url="https://benchmark.bidwise.local/recommendations",
            type_source="SITE_EMPLOI",
        )
        source_item_url = "https://benchmark.bidwise.local/recommendations/hybrid-accounting"
        Opportunite.objects.create(
            source=source,
            source_item_url=source_item_url,
            titre="Old title",
            description="Old description",
            organisation_nom="OldCo",
            ville="Tunis",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=datetime.now(dt_timezone.utc).date(),
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.9,
                    "family_confidence": 0.95,
                    "business_families": ["accounting_finance_audit"],
                },
                "custom_key": "keep-me",
            },
        )
        dataset = BenchmarkDataset(
            profiles=(),
            resumes={},
            opportunities=(
                BenchmarkOpportunity(
                    opportunity_id="hybrid-accounting",
                    title="Python Accountant Tool Specialist",
                    company="Finance Automation",
                    location="Sfax",
                    description="Python accounting automation role.",
                    skills=("Python", "Accounting", "Excel"),
                    industries=("accounting",),
                    language="EN",
                    type_opportunite=TypeOpportunite.EMPLOI,
                    contract_type="CDI",
                    availability="Full time",
                    experience_min=1,
                    experience_max=3,
                    confusing=True,
                ),
            ),
            expected={},
            report_dir=Path("benchmark_reports"),
            default_top_k=10,
            precision_good_threshold=0.8,
            precision_medium_threshold=0.5,
        )

        builder = DjangoBenchmarkFixtureBuilder()
        builder._ensure_opportunities(dataset, rebuild_embeddings=False, batch_size=1)

        opportunity = Opportunite.objects.get(source=source, source_item_url=source_item_url)
        self.assertEqual(opportunity.titre, "Python Accountant Tool Specialist")
        self.assertEqual(
            opportunity.extra_data["llm_enrichment"]["business_families"],
            ["accounting_finance_audit"],
        )
        self.assertEqual(opportunity.extra_data["custom_key"], "keep-me")
        self.assertTrue(opportunity.extra_data["benchmark"])
        self.assertEqual(opportunity.extra_data["benchmark_opportunity_id"], "hybrid-accounting")
        self.assertTrue(opportunity.extra_data["confusing"])


class RecommendationBenchmarkMetricTests(SimpleTestCase):
    def test_metrics_compute_precision_recall_noise_and_false_positives(self):
        expected = ExpectedResult(
            profile_id="backend",
            should_match=("Python Backend Developer", "Django Engineer"),
            should_not_match=("Accountant", "Nurse"),
        )
        results = [
            recommendation("Python Backend Developer", confidence="HIGH"),
            recommendation("Accountant", confidence="LOW"),
            recommendation("Django Engineer", confidence="MEDIUM"),
        ]

        metrics = metrics_for_recommendations(results, expected, top_k=3)

        self.assertEqual(metrics["precision_at_k"], 0.6667)
        self.assertEqual(metrics["recall_at_k"], 1.0)
        self.assertEqual(metrics["noise_rate"], 0.3333)
        self.assertEqual(metrics["false_positive_rate"], 0.3333)
        self.assertEqual(metrics["confidence_distribution"], {"LOW": 1, "MEDIUM": 1, "HIGH": 1})

    def test_cv_uplift_computation_rewards_profile_plus_cv_improvement(self):
        base = {
            "metrics": {
                "precision_at_k": 0.2,
                "average_semantic_score": 0.35,
                "noise_rate": 0.3,
                "mrr": 0.2,
                "exact_match_rate": 0.2,
            }
        }
        cv = {
            "metrics": {
                "precision_at_k": 0.8,
                "average_semantic_score": 0.72,
                "noise_rate": 0.0,
                "mrr": 1.0,
                "exact_match_rate": 0.8,
            }
        }

        uplift = compute_cv_uplift([(base, cv)])

        self.assertEqual(uplift["status"], "GOOD")
        self.assertGreater(uplift["relative_precision_uplift_percent"], 0)
        self.assertEqual(uplift["noise_reduction"], 0.3)

    def test_sparse_profile_robustness_uses_sparse_scenarios_and_confidence(self):
        reports = [
            {
                "profile_id": "sparse_python_01",
                "scenario": "profile_only",
                "categories": ["sparse"],
                "metrics": {
                    "noise_rate": 0.0,
                    "recommendation_count": 2,
                    "confidence_distribution": {"LOW": 1, "MEDIUM": 1, "HIGH": 0},
                },
            },
            {
                "profile_id": "backend_full",
                "scenario": "profile_only",
                "categories": ["backend"],
                "metrics": {
                    "noise_rate": 1.0,
                    "recommendation_count": 1,
                    "confidence_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 1},
                },
            },
        ]

        robustness = compute_sparse_profile_robustness(reports)

        self.assertEqual(robustness["status"], "GOOD")
        self.assertEqual(robustness["profile_count"], 1)

    def test_multilingual_robustness_keeps_language_breakdown(self):
        reports = [
            {"language": "EN", "metrics": {"precision_at_k": 1.0, "recall_at_k": 1.0, "noise_rate": 0.0, "exact_match_rate": 1.0, "false_positive_rate": 0.0, "recommendation_diversity": 1.0}},
            {"language": "FR", "metrics": {"precision_at_k": 0.6, "recall_at_k": 0.5, "noise_rate": 0.0, "exact_match_rate": 0.6, "false_positive_rate": 0.0, "recommendation_diversity": 1.0}},
            {"language": "AR", "metrics": {"precision_at_k": 0.5, "recall_at_k": 0.5, "noise_rate": 0.2, "exact_match_rate": 0.5, "false_positive_rate": 0.2, "recommendation_diversity": 1.0}},
        ]

        robustness = compute_multilingual_robustness(reports)

        self.assertIn("EN", robustness["breakdown"])
        self.assertIn("FR", robustness["breakdown"])
        self.assertIn("AR", robustness["breakdown"])
        self.assertEqual(robustness["breakdown"]["AR"]["status"], "MEDIUM")

    def test_semantic_extraction_metrics_are_reportable(self):
        reports = [
            {
                "language": "EN",
                "categories": ["backend"],
                "semantic_resume": {
                    "skills": ["python"],
                    "domains": ["backend"],
                    "tools": ["django", "postgresql"],
                    "has_structured_signal": True,
                },
            },
            {
                "language": "AR",
                "categories": ["backend"],
                "semantic_resume": {
                    "skills": ["python"],
                    "domains": ["backend"],
                    "tools": ["django"],
                    "has_structured_signal": True,
                },
            },
        ]

        metrics = compute_semantic_extraction_metrics(reports)

        self.assertEqual(metrics["semantic_extraction_precision"], 1.0)
        self.assertEqual(metrics["extracted_skill_relevance"], 1.0)
        self.assertEqual(metrics["multilingual_extraction_robustness"], "GOOD")

    def test_pgvector_array_payload_validation_avoids_truthiness_error(self):
        class ArrayLikeVector:
            def __init__(self, values):
                self.values = values

            def __bool__(self):
                raise ValueError("ambiguous truth value")

            def tolist(self):
                return list(self.values)

        self.assertTrue(_has_valid_vector_payload(ArrayLikeVector([1.0] + [0.0] * 383)))
        self.assertFalse(_has_valid_vector_payload(ArrayLikeVector([1.0, 0.0])))


class FakeFixtureBuilder:
    def ensure_fixtures(self, dataset, *, rebuild_embeddings=False, batch_size=32):
        return FixtureState(users_by_profile_id={}, opportunity_count=len(dataset.opportunities), embedding_model="fake-model")

    def prepare_profile_scenario(self, profile_spec, *, resume_text):
        return SimpleNamespace(profile_id=profile_spec.profile_id, resume_text=resume_text)


class RecommendationBenchmarkRunnerTests(SimpleTestCase):
    def build_dataset(self):
        return BenchmarkDataset(
            profiles=(
                BenchmarkProfile(
                    profile_id="sparse_python_01",
                    language="EN",
                    categories=("sparse", "backend"),
                    fields={"competences": ["Python"]},
                    cv_variant_ids=("cv_backend",),
                ),
                BenchmarkProfile(
                    profile_id="arabic_backend_01",
                    language="AR",
                    categories=("arabic", "backend"),
                    fields={"competences": ["بايثون"]},
                    cv_variant_ids=(),
                ),
            ),
            resumes={
                "cv_backend": BenchmarkResume(
                    resume_id="cv_backend",
                    language="EN",
                    specialization="backend",
                    text="Django backend API CV",
                )
            },
            expected={
                "sparse_python_01": ExpectedResult(
                    profile_id="sparse_python_01",
                    should_match=("Python Backend Developer",),
                    should_not_match=("Accountant",),
                    cv_expectations={
                        "cv_backend": {
                            "should_match": ("Django Engineer",),
                            "should_not_match": ("Accountant",),
                        }
                    },
                ),
                "arabic_backend_01": ExpectedResult(
                    profile_id="arabic_backend_01",
                    should_match=("مهندس برمجيات بايثون",),
                    should_not_match=("محاسب",),
                ),
            },
            opportunities=(
                BenchmarkOpportunity(
                    opportunity_id="python_backend",
                    title="Python Backend Developer",
                    description="Python backend API role",
                    company="Benchmark",
                    location="Tunis",
                    language="EN",
                    skills=("Python",),
                    industries=("Backend",),
                ),
            ),
            report_dir=Path("benchmark_reports"),
            default_top_k=3,
            precision_good_threshold=0.7,
            precision_medium_threshold=0.45,
        )

    def test_runner_generates_deterministic_report_with_fake_executor(self):
        dataset = self.build_dataset()

        def executor(user, limit):
            if user.profile_id == "sparse_python_01" and user.resume_text:
                return [recommendation("Django Engineer", confidence="HIGH", score=0.9, semantic_score=0.88)]
            if user.profile_id == "arabic_backend_01":
                return [recommendation("مهندس برمجيات بايثون", confidence="MEDIUM")]
            return [recommendation("Accountant", confidence="LOW", score=0.3, semantic_score=0.2)]

        runner = RecommendationBenchmarkRunner(
            dataset=dataset,
            fixture_builder=FakeFixtureBuilder(),
            recommendation_executor=executor,
        )
        options = BenchmarkRunOptions(
            top_k=3,
            write_report=False,
            generated_at=datetime(2026, 5, 8, 12, 0, tzinfo=dt_timezone.utc),
        )

        with patch("ai.recommendation_benchmark.runner.get_current_profile_embedding_model", return_value="fake-model"):
            first = runner.run(options)
            second = runner.run(options)

        self.assertEqual(first, second)
        self.assertEqual(first["metadata"]["profiles_tested"], 2)
        self.assertEqual(first["cv_uplift"]["status"], "GOOD")
        self.assertEqual(first["multilingual_robustness"]["breakdown"]["AR"]["status"], "GOOD")

    def test_report_generation_writes_machine_readable_json(self):
        dataset = self.build_dataset()
        runner = RecommendationBenchmarkRunner(
            dataset=dataset,
            fixture_builder=FakeFixtureBuilder(),
            recommendation_executor=lambda user, limit: [recommendation("Python Backend Developer")],
        )
        with TemporaryDirectory() as tmpdir:
            options = BenchmarkRunOptions(
                top_k=3,
                output_dir=Path(tmpdir),
                write_report=True,
                generated_at=datetime(2026, 5, 8, 12, 0, tzinfo=dt_timezone.utc),
            )
            with patch("ai.recommendation_benchmark.runner.get_current_profile_embedding_model", return_value="fake-model"):
                report = runner.run(options)

            path = Path(report["metadata"]["json_report_path"])
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["metadata"]["generated_at"], "2026-05-08T12:00:00+00:00")
            self.assertIn("profile_breakdown", payload)

    def test_console_report_contains_required_sections(self):
        report = {
            "metadata": {
                "embedding_model": "fake-model",
                "top_k": 10,
                "profiles_tested": 24,
                "scenarios_tested": 30,
                "language_coverage": ["AR", "EN", "FR"],
                "json_report_path": "backend/benchmark_reports/recommendation_benchmark_2026_05_08.json",
            },
            "overall_metrics": {
                "precision_at_k": 0.82,
                "recall_at_k": 0.79,
                "noise_rate": 0.08,
                "exact_match_rate": 0.82,
                "false_positive_rate": 0.06,
                "recommendation_diversity": 0.9,
                "confidence_calibration": {"status": "GOOD"},
            },
            "sparse_profile_robustness": {"status": "GOOD"},
            "cv_uplift": {"relative_precision_uplift_percent": 18.0},
            "multilingual_robustness": {"status": "MEDIUM"},
            "category_breakdown": [{"category": "backend", "status": "GOOD", "precision_at_k": 0.9, "noise_rate": 0.0}],
            "failures": ["Arabic accounting profiles less precise"],
        }

        rendered = format_console_report(report)

        self.assertIn("BIDWISE RECOMMENDATION BENCHMARK", rendered)
        self.assertIn("OVERALL METRICS", rendered)
        self.assertIn("CATEGORY BREAKDOWN", rendered)
        self.assertIn("TOP FAILURE CASES", rendered)
        self.assertIn("CV Uplift: +18%", rendered)

    def test_management_command_uses_runner_and_prints_report(self):
        report = {
            "metadata": {
                "embedding_model": "fake-model",
                "top_k": 3,
                "profiles_tested": 1,
                "scenarios_tested": 1,
                "language_coverage": ["EN"],
            },
            "overall_metrics": {
                "precision_at_k": 1.0,
                "recall_at_k": 1.0,
                "noise_rate": 0.0,
                "exact_match_rate": 1.0,
                "false_positive_rate": 0.0,
                "recommendation_diversity": 1.0,
                "confidence_calibration": {"status": "GOOD"},
            },
            "sparse_profile_robustness": {"status": "GOOD"},
            "cv_uplift": {"relative_precision_uplift_percent": 0.0},
            "multilingual_robustness": {"status": "GOOD"},
            "category_breakdown": [],
            "failures": [],
        }
        fake_runner = SimpleNamespace(
            dataset=SimpleNamespace(default_top_k=3),
            run=lambda options: report,
        )

        with patch(
            "opportunities.management.commands.benchmark_recommendations.RecommendationBenchmarkRunner",
            return_value=fake_runner,
        ):
            output = StringIO()
            call_command("benchmark_recommendations", "--no-write-report", stdout=output)

        self.assertIn("BIDWISE RECOMMENDATION BENCHMARK", output.getvalue())
