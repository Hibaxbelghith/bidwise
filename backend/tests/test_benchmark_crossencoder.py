from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from ai.recommendation_benchmark.dataset import (
    BenchmarkDataset,
    BenchmarkOpportunity,
    BenchmarkProfile,
    ExpectedResult,
)
from ai.recommendation_benchmark.fixtures import FixtureState
from ai.recommendation_benchmark.metrics import compute_crossencoder_uplift
from ai.recommendation_benchmark.runner import (
    BenchmarkRunOptions,
    RecommendationBenchmarkRunner,
    format_console_report,
)


def recommendation(title, *, score=0.7, confidence="MEDIUM"):
    return {
        "id": abs(hash(title)) % 10000,
        "title": title,
        "score": score,
        "match_score": score,
        "semantic_score": score,
        "business_score": 0.1,
        "recommendation_confidence": confidence,
        "company": "BenchmarkCo",
        "location": "Tunis",
        "type": "EMPLOI",
    }


def profile_report(profile_id, *, precision, false_positive, language="EN", categories=None):
    metrics = {
        "precision_at_k": precision,
        "recall_at_k": precision,
        "noise_rate": false_positive,
        "exact_match_rate": precision,
        "false_positive_rate": false_positive,
        "recommendation_diversity": 1.0,
    }
    return {
        "profile_id": profile_id,
        "scenario": "profile_only",
        "language": language,
        "categories": categories or [],
        "metrics": metrics,
        "top_3_metrics": metrics,
    }


class FakeFixtureBuilder:
    def ensure_fixtures(self, dataset, *, rebuild_embeddings=False, batch_size=32):
        return FixtureState(users_by_profile_id={}, opportunity_count=len(dataset.opportunities), embedding_model="fake")

    def prepare_profile_scenario(self, profile_spec, *, resume_text):
        return SimpleNamespace(profile_id=profile_spec.profile_id, resume_text=resume_text)


class BenchmarkCrossEncoderTests(SimpleTestCase):
    def test_crossencoder_uplift_metrics_compare_baseline_and_enabled_runs(self):
        baseline = [
            profile_report("backend", precision=0.5, false_positive=0.5, categories=["backend"]),
            profile_report("sparse", precision=0.0, false_positive=0.5, categories=["sparse"]),
            profile_report("arabic", precision=0.5, false_positive=0.5, language="AR", categories=["multilingual"]),
        ]
        enabled = [
            profile_report("backend", precision=1.0, false_positive=0.0, categories=["backend"]),
            profile_report("sparse", precision=0.5, false_positive=0.0, categories=["sparse"]),
            profile_report("arabic", precision=1.0, false_positive=0.0, language="AR", categories=["multilingual"]),
        ]

        uplift = compute_crossencoder_uplift(baseline, enabled)

        self.assertGreater(uplift["precision_uplift_percent"], 0)
        self.assertLess(uplift["false_positive_rate_delta_percent"], 0)
        self.assertGreater(uplift["top_3_precision_uplift_percent"], 0)
        self.assertGreater(uplift["sparse_profile_uplift_percent"], 0)
        self.assertGreater(uplift["multilingual_uplift_percent"], 0)

    def test_runner_verifies_crossencoder_benchmark_uplift(self):
        dataset = BenchmarkDataset(
            profiles=(
                BenchmarkProfile(
                    profile_id="backend",
                    language="EN",
                    categories=("backend",),
                    fields={"competences": ["Python"]},
                ),
            ),
            resumes={},
            expected={
                "backend": ExpectedResult(
                    profile_id="backend",
                    should_match=("Python Backend Developer",),
                    should_not_match=("Accounting Assistant",),
                ),
            },
            opportunities=(
                BenchmarkOpportunity(
                    opportunity_id="python_backend",
                    title="Python Backend Developer",
                    description="Python backend API role",
                    company="BenchmarkCo",
                    location="Tunis",
                    language="EN",
                    skills=("Python",),
                    industries=("Backend",),
                ),
            ),
            report_dir=Path("benchmark_reports"),
            default_top_k=2,
            precision_good_threshold=0.7,
            precision_medium_threshold=0.45,
        )

        def executor(user, limit):
            if settings.CROSS_ENCODER_ENABLED:
                return [recommendation("Python Backend Developer", confidence="HIGH")]
            return [recommendation("Accounting Assistant", confidence="LOW")]

        runner = RecommendationBenchmarkRunner(
            dataset=dataset,
            fixture_builder=FakeFixtureBuilder(),
            recommendation_executor=executor,
        )
        options = BenchmarkRunOptions(
            top_k=2,
            write_report=False,
            generated_at=datetime(2026, 5, 8, 12, 0, tzinfo=dt_timezone.utc),
            crossencoder_comparison=True,
        )

        with patch("ai.recommendation_benchmark.runner.get_current_profile_embedding_model", return_value="fake"):
            report = runner.run(options)

        comparison = report["crossencoder_comparison"]
        self.assertGreater(comparison["precision_delta"], 0)
        self.assertLess(comparison["false_positive_rate_delta"], 0)

    def test_console_report_includes_crossencoder_uplift_lines(self):
        report = {
            "metadata": {
                "embedding_model": "fake-model",
                "crossencoder_enabled": True,
                "top_k": 10,
                "profiles_tested": 1,
                "scenarios_tested": 1,
                "language_coverage": ["EN"],
            },
            "overall_metrics": {
                "precision_at_k": 0.9,
                "recall_at_k": 0.8,
                "noise_rate": 0.0,
                "exact_match_rate": 0.9,
                "false_positive_rate": 0.0,
                "recommendation_diversity": 1.0,
                "confidence_calibration": {"status": "GOOD"},
            },
            "sparse_profile_robustness": {"status": "GOOD"},
            "cv_uplift": {"relative_precision_uplift_percent": 0.0},
            "multilingual_robustness": {"status": "GOOD"},
            "semantic_extraction": {"semantic_extraction_precision": 1.0},
            "crossencoder_comparison": {
                "precision_uplift_percent": 20.0,
                "false_positive_rate_delta_percent": -15.0,
                "top_3_precision_uplift_percent": 30.0,
                "sparse_profile_uplift_percent": 10.0,
                "multilingual_uplift_percent": 12.0,
            },
            "category_breakdown": [],
            "failures": [],
        }

        rendered = format_console_report(report)

        self.assertIn("CrossEncoder Enabled: YES", rendered)
        self.assertIn("Precision@10 uplift: +20%", rendered)
        self.assertIn("False positive reduction: -15%", rendered)
        self.assertIn("Top-3 relevance uplift: +30%", rendered)
