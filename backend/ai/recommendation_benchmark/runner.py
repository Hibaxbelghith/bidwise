from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from typing import Any, Callable

from django.test.utils import override_settings
from django.utils import timezone

from ai.crossencoder.loader import get_cross_encoder_status
from ai.embeddings import get_current_profile_embedding_model
from ai.views import _build_recommendations

from .dataset import BenchmarkDataset, BenchmarkProfile, load_benchmark_dataset
from .fixtures import DjangoBenchmarkFixtureBuilder, FixtureState
from .metrics import (
    aggregate_metric_dicts,
    compute_cv_uplift,
    compute_crossencoder_uplift,
    compute_multilingual_robustness,
    compute_semantic_extraction_metrics,
    compute_sparse_profile_robustness,
    metrics_for_recommendations,
    normalize_title,
    recommendation_title,
    status_for_precision_noise,
)


RecommendationExecutor = Callable[[Any, int], list[dict[str, Any]]]


def default_recommendation_executor(user: Any, limit: int) -> list[dict[str, Any]]:
    return list(_build_recommendations(SimpleNamespace(user=user), limit))


@dataclass
class BenchmarkRunOptions:
    top_k: int = 10
    rebuild_embeddings: bool = False
    batch_size: int = 32
    write_report: bool = True
    output_dir: Path | None = None
    generated_at: datetime | None = None
    crossencoder_comparison: bool = True


class RecommendationBenchmarkRunner:
    def __init__(
        self,
        *,
        dataset: BenchmarkDataset | None = None,
        fixture_builder: Any | None = None,
        recommendation_executor: RecommendationExecutor | None = None,
    ) -> None:
        self.dataset = dataset or load_benchmark_dataset()
        self.fixture_builder = fixture_builder or DjangoBenchmarkFixtureBuilder()
        self.recommendation_executor = recommendation_executor

    def run(self, options: BenchmarkRunOptions | None = None) -> dict[str, Any]:
        options = options or BenchmarkRunOptions(top_k=self.dataset.default_top_k)
        top_k = int(options.top_k or self.dataset.default_top_k)
        fixture_state = self.fixture_builder.ensure_fixtures(
            self.dataset,
            rebuild_embeddings=options.rebuild_embeddings,
            batch_size=options.batch_size,
        )

        baseline_reports: list[dict[str, Any]] = []
        if options.crossencoder_comparison:
            with override_settings(CROSS_ENCODER_ENABLED=False):
                baseline_reports, _ = self._run_all_profile_scenarios(top_k)

        with override_settings(CROSS_ENCODER_ENABLED=True):
            profile_reports, cv_pairs = self._run_all_profile_scenarios(top_k)

        report = self._build_report(
            fixture_state=fixture_state,
            profile_reports=profile_reports,
            baseline_reports=baseline_reports,
            cv_pairs=cv_pairs,
            top_k=top_k,
            generated_at=options.generated_at,
            crossencoder_comparison=options.crossencoder_comparison,
        )
        if options.write_report:
            output_dir = options.output_dir or self.dataset.report_dir
            report["metadata"]["json_report_path"] = str(write_json_report(report, output_dir=output_dir))
        return report

    def _run_all_profile_scenarios(
        self,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], list[tuple[dict[str, Any], dict[str, Any]]]]:
        profile_reports: list[dict[str, Any]] = []
        cv_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []

        for profile_spec in self.dataset.profiles:
            base_report = self._run_profile_scenario(
                profile_spec,
                resume_id=None,
                resume_text=None,
                scenario="profile_only",
                top_k=top_k,
            )
            profile_reports.append(base_report)

            for resume_id in profile_spec.cv_variant_ids:
                resume = self.dataset.resumes[resume_id]
                cv_report = self._run_profile_scenario(
                    profile_spec,
                    resume_id=resume_id,
                    resume_text=resume.text,
                    scenario=f"profile_plus_cv:{resume.specialization or resume_id}",
                    top_k=top_k,
                )
                profile_reports.append(cv_report)
                cv_pairs.append((base_report, cv_report))

        return profile_reports, cv_pairs

    def _run_profile_scenario(
        self,
        profile_spec: BenchmarkProfile,
        *,
        resume_id: str | None,
        resume_text: str | None,
        scenario: str,
        top_k: int,
    ) -> dict[str, Any]:
        user = self.fixture_builder.prepare_profile_scenario(
            profile_spec,
            resume_text=resume_text,
        )
        recommendations = self._execute_recommendations(user, top_k)
        expected = self.dataset.expectation_for(profile_spec.profile_id, resume_id)
        metrics = metrics_for_recommendations(recommendations, expected, top_k)
        top_3_metrics = metrics_for_recommendations(recommendations, expected, min(3, top_k))
        retrieved_jobs = [_serialize_retrieved_job(item) for item in recommendations[:top_k]]
        failures = _failure_cases(
            profile_id=profile_spec.profile_id,
            scenario=scenario,
            recommendations=recommendations[:top_k],
            expected_matches=expected.should_match,
            expected_non_matches=expected.should_not_match,
            precision=metrics["precision_at_k"],
        )
        return {
            "profile_id": profile_spec.profile_id,
            "scenario": scenario,
            "resume_id": resume_id,
            "language": profile_spec.language,
            "categories": list(profile_spec.categories),
            "metrics": metrics,
            "top_3_metrics": top_3_metrics,
            "semantic_resume": _semantic_resume_summary(getattr(user, "profil", None)),
            "retrieved_jobs": retrieved_jobs,
            "failures": failures,
        }

    def _execute_recommendations(self, user: Any, top_k: int) -> list[dict[str, Any]]:
        if self.recommendation_executor is not None:
            return list(self.recommendation_executor(user, top_k))
        benchmark_executor = getattr(self.fixture_builder, "execute_recommendations", None)
        if callable(benchmark_executor):
            return list(benchmark_executor(user, top_k))
        return default_recommendation_executor(user, top_k)

    def _build_report(
        self,
        *,
        fixture_state: FixtureState,
        profile_reports: list[dict[str, Any]],
        baseline_reports: list[dict[str, Any]],
        cv_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
        top_k: int,
        generated_at: datetime | None,
        crossencoder_comparison: bool,
    ) -> dict[str, Any]:
        generated_at = generated_at or timezone.now()
        scenario_metrics = [row["metrics"] for row in profile_reports]
        overall = aggregate_metric_dicts(scenario_metrics)
        calibration_scores = [
            float(row["metrics"]["confidence_calibration"]["score"])
            for row in profile_reports
        ]
        overall["confidence_calibration"] = {
            "score": round(mean(calibration_scores), 4) if calibration_scores else 0.0,
            "status": _status_for_calibration(mean(calibration_scores) if calibration_scores else 0.0),
        }
        overall["status"] = status_for_precision_noise(
            overall["precision_at_k"],
            overall["noise_rate"],
        )

        category_breakdown = _category_breakdown(profile_reports)
        failures = [failure for row in profile_reports for failure in row["failures"]]
        failures = failures[:10]

        return {
            "metadata": {
                "generated_at": generated_at.replace(microsecond=0).isoformat(),
                "embedding_model": get_current_profile_embedding_model(),
                "fixture_embedding_model": fixture_state.embedding_model,
                "crossencoder_enabled": True,
                "crossencoder_status": _stable_crossencoder_status(),
                "top_k": top_k,
                "profiles_tested": len(self.dataset.profiles),
                "scenarios_tested": len(profile_reports),
                "opportunities_loaded": fixture_state.opportunity_count,
                "language_coverage": sorted({profile.language for profile in self.dataset.profiles}),
            },
            "overall_metrics": overall,
            "category_breakdown": category_breakdown,
            "sparse_profile_robustness": compute_sparse_profile_robustness(profile_reports),
            "cv_uplift": compute_cv_uplift(cv_pairs),
            "multilingual_robustness": compute_multilingual_robustness(profile_reports),
            "semantic_extraction": compute_semantic_extraction_metrics(profile_reports),
            "crossencoder_comparison": (
                compute_crossencoder_uplift(baseline_reports, profile_reports)
                if crossencoder_comparison
                else {}
            ),
            "profile_breakdown": profile_reports,
            "failures": failures,
            "confidence_distribution": _aggregate_confidence(profile_reports),
        }


def _serialize_retrieved_job(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": recommendation_title(item),
        "score": round(float(item.get("score") or item.get("match_score") or 0.0), 4),
        "semantic_score": round(float(item.get("semantic_score") or 0.0), 4),
        "business_score": round(float(item.get("business_score") or 0.0), 4),
        "confidence": item.get("recommendation_confidence") or "LOW",
        "company": item.get("company") or "",
        "location": item.get("location") or "",
        "type": item.get("type") or "",
    }


def _semantic_resume_summary(profile: Any) -> dict[str, Any] | None:
    if profile is None or not hasattr(profile, "resumes"):
        return None
    try:
        resume = profile.resumes.filter(is_active=True).only(
            "extracted_skills",
            "extracted_domains",
            "extracted_tools",
            "extracted_languages",
            "semantic_resume_confidence",
            "semantic_resume_status",
            "semantic_resume_version",
        ).first()
    except Exception:
        return None
    if not resume:
        return None
    skills = list(getattr(resume, "extracted_skills", []) or [])
    domains = list(getattr(resume, "extracted_domains", []) or [])
    tools = list(getattr(resume, "extracted_tools", []) or [])
    return {
        "skills": skills,
        "domains": domains,
        "tools": tools,
        "languages_detected": list(getattr(resume, "extracted_languages", []) or []),
        "semantic_confidence": round(float(getattr(resume, "semantic_resume_confidence", 0.0) or 0.0), 4),
        "semantic_status": getattr(resume, "semantic_resume_status", ""),
        "semantic_version": getattr(resume, "semantic_resume_version", ""),
        "has_structured_signal": bool(skills or domains or tools),
    }


def _failure_cases(
    *,
    profile_id: str,
    scenario: str,
    recommendations: list[dict[str, Any]],
    expected_matches: tuple[str, ...],
    expected_non_matches: tuple[str, ...],
    precision: float,
) -> list[str]:
    failures = []
    expected_match_set = {normalize_title(title) for title in expected_matches}
    expected_non_match_set = {normalize_title(title) for title in expected_non_matches}
    retrieved_titles = {normalize_title(recommendation_title(item)) for item in recommendations}
    noisy = retrieved_titles.intersection(expected_non_match_set)
    if noisy:
        failures.append(
            f"{profile_id} [{scenario}] retrieved disallowed titles: {', '.join(sorted(noisy))}"
        )
    missed = expected_match_set.difference(retrieved_titles)
    if missed and precision < 0.50:
        failures.append(
            f"{profile_id} [{scenario}] missed expected titles: {', '.join(sorted(missed)[:3])}"
        )
    if precision < 0.35:
        failures.append(f"{profile_id} [{scenario}] precision below benchmark floor: {precision:.2f}")
    return failures


def _category_breakdown(profile_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in profile_reports:
        for category in row.get("categories", []):
            grouped.setdefault(category, []).append(row["metrics"])

    breakdown = []
    for category, rows in sorted(grouped.items()):
        aggregate = aggregate_metric_dicts(rows)
        aggregate["category"] = category
        aggregate["status"] = status_for_precision_noise(
            aggregate["precision_at_k"],
            aggregate["noise_rate"],
        )
        breakdown.append(aggregate)
    return breakdown


def _status_for_calibration(score: float) -> str:
    if score >= 0.70:
        return "GOOD"
    if score >= 0.50:
        return "MEDIUM"
    return "LOW"


def _aggregate_confidence(profile_reports: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for row in profile_reports:
        for level, count in row["metrics"].get("confidence_distribution", {}).items():
            totals[level] = totals.get(level, 0) + int(count)
    return totals


def _stable_crossencoder_status() -> dict[str, Any]:
    status = dict(get_cross_encoder_status())
    status.pop("unavailable_for_seconds", None)
    status["unavailable"] = bool(status.get("unavailable_reason"))
    return status


def write_json_report(report: dict[str, Any], *, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = report["metadata"]["generated_at"]
    date_part = generated_at[:10].replace("-", "_")
    path = output_dir / f"recommendation_benchmark_{date_part}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def format_console_report(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    overall = report["overall_metrics"]
    sparse = report["sparse_profile_robustness"]
    cv = report["cv_uplift"]
    multilingual = report["multilingual_robustness"]
    semantic = report.get("semantic_extraction", {})
    crossencoder = report.get("crossencoder_comparison") or {}
    language_coverage = "/".join(metadata.get("language_coverage", []))
    lines = [
        "=" * 50,
        "BIDWISE RECOMMENDATION BENCHMARK",
        "=" * 50,
        "",
        f"Embedding model: {metadata['embedding_model']}",
        f"CrossEncoder Enabled: {'YES' if metadata.get('crossencoder_enabled') else 'NO'}",
        f"Profiles tested: {metadata['profiles_tested']}",
        f"Scenarios tested: {metadata['scenarios_tested']}",
        f"Language coverage: {language_coverage}",
        "",
        "-" * 50,
        "OVERALL METRICS",
        "-" * 50,
        "",
        f"Precision@{metadata['top_k']}: {overall['precision_at_k']:.2f}",
        f"Recall@{metadata['top_k']}: {overall['recall_at_k']:.2f}",
        f"Noise Rate: {overall['noise_rate']:.2f}",
        f"Exact Match Rate: {overall['exact_match_rate']:.2f}",
        f"Sparse Profile Robustness: {sparse.get('status', 'N/A')}",
        f"CV Uplift: {cv.get('relative_precision_uplift_percent', 0.0):+.0f}%",
        f"Multilingual Robustness: {multilingual.get('status', 'N/A')}",
        f"Semantic Extraction Precision: {semantic.get('semantic_extraction_precision', 0.0):.2f}",
        f"Multilingual Extraction Robustness: {semantic.get('multilingual_extraction_robustness', 'N/A')}",
        f"Confidence Calibration: {overall['confidence_calibration']['status']}",
        f"Recommendation Diversity: {overall['recommendation_diversity']:.2f}",
        f"False Positive Rate: {overall['false_positive_rate']:.2f}",
    ]
    if crossencoder:
        lines.extend([
            f"Precision@{metadata['top_k']} uplift: {crossencoder.get('precision_uplift_percent', 0.0):+.0f}%",
            f"False positive reduction: {crossencoder.get('false_positive_rate_delta_percent', 0.0):+.0f}%",
            f"Top-3 relevance uplift: {crossencoder.get('top_3_precision_uplift_percent', 0.0):+.0f}%",
            f"Sparse profile uplift: {crossencoder.get('sparse_profile_uplift_percent', 0.0):+.0f}%",
            f"Multilingual uplift: {crossencoder.get('multilingual_uplift_percent', 0.0):+.0f}%",
        ])
    lines.extend([
        "",
        "-" * 50,
        "CATEGORY BREAKDOWN",
        "-" * 50,
        "",
    ])
    for row in report["category_breakdown"]:
        lines.append(f"{row['category']}: {row['status']} (P={row['precision_at_k']:.2f}, noise={row['noise_rate']:.2f})")

    lines.extend([
        "",
        "-" * 50,
        "TOP FAILURE CASES",
        "-" * 50,
        "",
    ])
    failures = report.get("failures") or []
    if failures:
        lines.extend(f"- {failure}" for failure in failures[:5])
    else:
        lines.append("- No benchmark failure cases above reporting thresholds.")

    report_path = metadata.get("json_report_path")
    if report_path:
        lines.extend(["", f"JSON report: {report_path}"])
    lines.extend(["", "=" * 50])
    return "\n".join(lines)
