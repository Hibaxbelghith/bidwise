from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from statistics import mean

from django.core.management.base import BaseCommand
from django.test.utils import override_settings
from django.utils import timezone

from ai.recommendation_benchmark.runner import (
    BenchmarkRunOptions,
    RecommendationBenchmarkRunner,
)


def _metric_delta(after: dict[str, float], before: dict[str, float], key: str) -> float:
    return round(float(after.get(key) or 0.0) - float(before.get(key) or 0.0), 4)


def _scenario_index(report: dict[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(row.get("profile_id") or ""), str(row.get("scenario") or "")): row
        for row in list(report.get("profile_breakdown") or [])
        if isinstance(row, dict)
    }


def _changed_scenarios(before: dict[str, object], after: dict[str, object], *, top_n: int = 10) -> list[dict[str, object]]:
    before_index = _scenario_index(before)
    after_index = _scenario_index(after)
    rows = []
    for key, after_row in after_index.items():
        before_row = before_index.get(key)
        if before_row is None:
            continue
        before_metrics = dict(before_row.get("metrics") or {})
        after_metrics = dict(after_row.get("metrics") or {})
        precision_delta = _metric_delta(after_metrics, before_metrics, "precision_at_k")
        noise_delta = _metric_delta(after_metrics, before_metrics, "noise_rate")
        exact_delta = _metric_delta(after_metrics, before_metrics, "exact_match_rate")
        if precision_delta == 0.0 and noise_delta == 0.0 and exact_delta == 0.0:
            continue
        before_jobs = [str(item.get("title") or "") for item in list(before_row.get("retrieved_jobs") or [])[:5]]
        after_jobs = [str(item.get("title") or "") for item in list(after_row.get("retrieved_jobs") or [])[:5]]
        rows.append(
            {
                "profile_id": key[0],
                "scenario": key[1],
                "precision_delta": precision_delta,
                "noise_delta": noise_delta,
                "exact_match_delta": exact_delta,
                "before_top_5": before_jobs,
                "after_top_5": after_jobs,
            }
        )
    rows.sort(
        key=lambda row: (
            -abs(float(row["precision_delta"])),
            -abs(float(row["noise_delta"])),
            row["profile_id"],
            row["scenario"],
        )
    )
    return rows[:top_n]


class Command(BaseCommand):
    help = "Compare recommendation benchmark results before/after normalized ESCO bonus for stabilization audits."

    def add_arguments(self, parser):
        parser.add_argument("--top-k", type=int, default=None)
        parser.add_argument("--batch-size", type=int, default=32)
        parser.add_argument("--rebuild-embeddings", action="store_true")
        parser.add_argument("--output-dir", default=None)
        parser.add_argument("--no-write-report", action="store_true")
        parser.add_argument("--no-crossencoder-comparison", action="store_true")
        parser.add_argument(
            "--max-profiles",
            type=int,
            default=None,
            help="Optional cap for a lighter stabilization benchmark run.",
        )
        parser.add_argument(
            "--profile-ids",
            nargs="+",
            default=None,
            help="Optional explicit benchmark profile ids to run.",
        )
        parser.add_argument(
            "--profile-only",
            action="store_true",
            help="Benchmark only base profile scenarios and skip CV variants for faster stabilization checks.",
        )

    def handle(self, *args, **options):
        runner = RecommendationBenchmarkRunner()
        selected_profile_ids = [str(value).strip() for value in list(options.get("profile_ids") or []) if str(value).strip()]
        max_profiles = options.get("max_profiles")
        if selected_profile_ids or max_profiles:
            selected_profiles = list(runner.dataset.profiles)
            if selected_profile_ids:
                selected_id_set = set(selected_profile_ids)
                selected_profiles = [
                    profile for profile in selected_profiles
                    if profile.profile_id in selected_id_set
                ]
            if max_profiles:
                selected_profiles = selected_profiles[: max(1, int(max_profiles))]
            if bool(options.get("profile_only")):
                selected_profiles = [
                    replace(profile, cv_variant_ids=())
                    for profile in selected_profiles
                ]
            selected_resume_ids = {
                resume_id
                for profile in selected_profiles
                for resume_id in profile.cv_variant_ids
            }
            selected_expected = {
                profile.profile_id: runner.dataset.expected[profile.profile_id]
                for profile in selected_profiles
            }
            runner.dataset = replace(
                runner.dataset,
                profiles=tuple(selected_profiles),
                resumes={
                    resume_id: resume
                    for resume_id, resume in runner.dataset.resumes.items()
                    if resume_id in selected_resume_ids
                },
                expected=selected_expected,
            )
        top_k = int(options.get("top_k") or runner.dataset.default_top_k)
        output_root = (
            Path(str(options["output_dir"]))
            if options.get("output_dir")
            else runner.dataset.report_dir / "stability"
        )
        output_root.mkdir(parents=True, exist_ok=True)
        generated_at = timezone.now()

        def _build_options(output_dir: Path) -> BenchmarkRunOptions:
            return BenchmarkRunOptions(
                top_k=max(1, top_k),
                rebuild_embeddings=bool(options.get("rebuild_embeddings")),
                batch_size=max(1, int(options.get("batch_size") or 32)),
                write_report=not bool(options.get("no_write_report")),
                output_dir=output_dir,
                generated_at=generated_at,
                crossencoder_comparison=not bool(options.get("no_crossencoder_comparison")),
            )

        with override_settings(RECOMMENDATION_ENABLE_NORMALIZED_SKILL_BONUS=False):
            before_report = runner.run(_build_options(output_root / "before"))

        with override_settings(RECOMMENDATION_ENABLE_NORMALIZED_SKILL_BONUS=True):
            after_report = runner.run(_build_options(output_root / "after"))

        before_metrics = dict(before_report.get("overall_metrics") or {})
        after_metrics = dict(after_report.get("overall_metrics") or {})
        delta = {
            "precision_at_k": _metric_delta(after_metrics, before_metrics, "precision_at_k"),
            "recall_at_k": _metric_delta(after_metrics, before_metrics, "recall_at_k"),
            "noise_rate": _metric_delta(after_metrics, before_metrics, "noise_rate"),
            "exact_match_rate": _metric_delta(after_metrics, before_metrics, "exact_match_rate"),
            "false_positive_rate": _metric_delta(after_metrics, before_metrics, "false_positive_rate"),
            "recommendation_diversity": _metric_delta(after_metrics, before_metrics, "recommendation_diversity"),
        }
        changed = _changed_scenarios(before_report, after_report)
        summary = {
            "generated_at": generated_at.replace(microsecond=0).isoformat(),
            "top_k": top_k,
            "before": before_metrics,
            "after": after_metrics,
            "delta": delta,
            "changed_scenarios": changed,
            "average_confidence_calibration_delta": round(
                float((after_metrics.get("confidence_calibration") or {}).get("score") or 0.0)
                - float((before_metrics.get("confidence_calibration") or {}).get("score") or 0.0),
                4,
            ),
            "mean_changed_precision_delta": round(
                mean(float(row["precision_delta"]) for row in changed),
                4,
            ) if changed else 0.0,
            "before_json_report": before_report.get("metadata", {}).get("json_report_path"),
            "after_json_report": after_report.get("metadata", {}).get("json_report_path"),
        }

        if not bool(options.get("no_write_report")):
            summary_path = output_root / f"recommendation_stability_{generated_at:%Y_%m_%d}.json"
            with summary_path.open("w", encoding="utf-8") as handle:
                json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            summary["summary_json_report"] = str(summary_path)

        self.stdout.write("Recommendation stability benchmark complete")
        self.stdout.write(
            "Before: P@%s=%0.2f noise=%0.2f FPR=%0.2f"
            % (
                top_k,
                float(before_metrics.get("precision_at_k") or 0.0),
                float(before_metrics.get("noise_rate") or 0.0),
                float(before_metrics.get("false_positive_rate") or 0.0),
            )
        )
        self.stdout.write(
            "After:  P@%s=%0.2f noise=%0.2f FPR=%0.2f"
            % (
                top_k,
                float(after_metrics.get("precision_at_k") or 0.0),
                float(after_metrics.get("noise_rate") or 0.0),
                float(after_metrics.get("false_positive_rate") or 0.0),
            )
        )
        self.stdout.write(
            "Delta:  precision=%+0.2f recall=%+0.2f noise=%+0.2f fpr=%+0.2f diversity=%+0.2f"
            % (
                delta["precision_at_k"],
                delta["recall_at_k"],
                delta["noise_rate"],
                delta["false_positive_rate"],
                delta["recommendation_diversity"],
            )
        )
        if changed:
            self.stdout.write("Top changed scenarios:")
            for row in changed[:5]:
                self.stdout.write(
                    "- %s [%s] precision=%+0.2f noise=%+0.2f exact=%+0.2f"
                    % (
                        row["profile_id"],
                        row["scenario"],
                        float(row["precision_delta"]),
                        float(row["noise_delta"]),
                        float(row["exact_match_delta"]),
                    )
                )
        if summary.get("summary_json_report"):
            self.stdout.write(f"Summary JSON: {summary['summary_json_report']}")
