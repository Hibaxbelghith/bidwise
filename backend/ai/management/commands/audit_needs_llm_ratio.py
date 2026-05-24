from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from ai.embeddings import build_user_embedding_text
from ai.jobbert import (
    build_precomputed_jobbert_scores,
    generate_jobbert_embeddings_batch,
    jobbert_model_name,
)
from ai.management.commands.audit_final_recommendations import (
    QUERYSET_FIELDS,
    _build_features,
    _clean_text,
    _float,
)
from ai.management.commands.benchmark_final_recommendation_profiles import (
    BENCHMARK_SOURCE_NAME,
    LLM_VALIDATION_MIN_SCORE,
    _issue_name,
    _should_validate_llm_hierarchy,
)
from ai.quality_gates import build_recommendation_evidence, classify_recommendation_bucket
from ai.recommendation_service import rank_opportunities
from ai.validation_profiles import VALIDATION_PROFILES, scenario_options
from opportunities.models import Opportunite, StatutOpportunite


def _ratio_status(ratio: float) -> str:
    if ratio <= 0.30:
        return "OK"
    if ratio <= 0.50:
        return "WATCH"
    return "TOO_HIGH"


def _compact_needs_llm_row(
    opportunity,
    bucket: str,
    bucket_reason: str,
    *,
    llm_validation_eligible: bool,
) -> dict[str, Any]:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
    return {
        "id": getattr(opportunity, "pk", None),
        "title": getattr(opportunity, "titre", ""),
        "company": getattr(opportunity, "organisation_nom", ""),
        "location": getattr(opportunity, "ville", ""),
        "source": getattr(getattr(opportunity, "source", None), "nom", "") or "",
        "final_score": _float(getattr(opportunity, "match_score", 0.0)),
        "jobbert_score": _float(debug.get("jobbert_score")) if isinstance(debug, dict) else 0.0,
        "bucket": bucket,
        "bucket_reason": bucket_reason,
        "llm_validation_eligible": llm_validation_eligible,
        "hierarchy_issue": _issue_name({"hierarchy_validation": validation}),
        "hierarchy_reason": str((validation or {}).get("reason") or ""),
        "seniority_gap": int((validation or {}).get("seniority_gap") or 0),
        "qualification_gap": int((validation or {}).get("qualification_gap") or 0),
        "responsibility_gap": int((validation or {}).get("responsibility_gap") or 0),
        "reasons": list(getattr(opportunity, "reason", []) or [])[:5],
    }


class Command(BaseCommand):
    help = "Audit how often top recommendations require LLM hierarchy validation."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="all")
        parser.add_argument("--candidate-limit", type=int, default=1700)
        parser.add_argument("--rerank-candidates", type=int, default=120)
        parser.add_argument("--top", type=int, default=10)
        parser.add_argument(
            "--llm-min-score",
            type=float,
            default=LLM_VALIDATION_MIN_SCORE,
            help="Minimum final score for validating RELATED_REVIEW needs_llm rows.",
        )
        parser.add_argument("--include-benchmark", action="store_true")
        parser.add_argument(
            "--profiles",
            default="all",
            help="Comma-separated benchmark scenario keys, or 'all'.",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument(
            "--output-json",
            default="",
            help="Optional path where the audit JSON payload will be written.",
        )

    def handle(self, *args, **options):
        model_name = jobbert_model_name()
        source_name = str(options.get("source") or "all").strip()
        candidate_limit = max(1, min(int(options.get("candidate_limit") or 1700), 5000))
        rerank_limit = max(1, min(int(options.get("rerank_candidates") or 120), candidate_limit))
        top_n = max(1, min(int(options.get("top") or 10), 100))
        llm_min_score = max(0.0, min(float(options.get("llm_min_score") or LLM_VALIDATION_MIN_SCORE), 1.0))
        requested_profiles = {
            item.strip()
            for item in str(options.get("profiles") or "all").split(",")
            if item.strip()
        }
        scenarios = [
            scenario
            for scenario in VALIDATION_PROFILES
            if "all" in requested_profiles or scenario.key in requested_profiles
        ]
        if not scenarios:
            raise CommandError("No matching benchmark profiles selected.")

        queryset = (
            Opportunite.objects.filter(
                statut=StatutOpportunite.ACTIVE,
                jobbert_embedding_model=model_name,
            )
            .exclude(jobbert_embedding_vector__isnull=True)
            .select_related("source")
            .only(*QUERYSET_FIELDS)
            .order_by("-date_publication", "-id")
        )
        if source_name and source_name.casefold() != "all":
            queryset = queryset.filter(source__nom__iexact=source_name)
        elif not bool(options.get("include_benchmark")):
            queryset = queryset.exclude(source__nom__iexact=BENCHMARK_SOURCE_NAME)

        candidates = list(queryset[:candidate_limit])
        if not candidates:
            raise CommandError("No JobBERT-embedded candidates found. Generate opportunity embeddings first.")

        profile_payloads = []
        global_issues = Counter()
        for scenario in scenarios:
            options_for_scenario = scenario_options(scenario)
            features = _build_features(options_for_scenario, scenario.profile_text)
            profile_semantic_text = build_user_embedding_text(features) or scenario.profile_text
            profile_vector = generate_jobbert_embeddings_batch(
                [profile_semantic_text],
                model_name=model_name,
                batch_size=1,
            )[0]
            raw_jobbert_scores = build_precomputed_jobbert_scores(profile_vector, candidates)
            if not raw_jobbert_scores:
                raise CommandError(f"No compatible JobBERT vectors for profile: {scenario.key}")

            selected = sorted(
                candidates,
                key=lambda item: raw_jobbert_scores.get(int(getattr(item, "id", 0) or 0), 0.0),
                reverse=True,
            )[:rerank_limit]
            ranking_features = dict(features)
            ranking_features["_jobbert_profile_vector"] = profile_vector
            ranked = rank_opportunities(
                [],
                selected,
                features=ranking_features,
                mode="partial",
                top_k=top_n,
                min_score=0.0,
            )

            needs_llm_rows = []
            issue_counts = Counter()
            llm_eligible_count = 0
            for opportunity in ranked:
                evidence = build_recommendation_evidence(ranking_features, opportunity)
                bucket, bucket_reason = classify_recommendation_bucket(
                    features=ranking_features,
                    opportunity=opportunity,
                    evidence=evidence,
                )
                debug = getattr(opportunity, "recommendation_debug", {}) or {}
                validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
                issue = _issue_name({"hierarchy_validation": validation})
                issue_counts[issue] += 1
                global_issues[issue] += 1
                if isinstance(validation, dict) and validation.get("needs_llm"):
                    llm_eligible = _should_validate_llm_hierarchy(
                        opportunity,
                        bucket,
                        min_score=llm_min_score,
                    )
                    if llm_eligible:
                        llm_eligible_count += 1
                    needs_llm_rows.append(
                        _compact_needs_llm_row(
                            opportunity,
                            bucket,
                            bucket_reason,
                            llm_validation_eligible=llm_eligible,
                        )
                    )

            needs_llm_count = len(needs_llm_rows)
            ratio = round(needs_llm_count / max(1, len(ranked)), 4)
            eligible_ratio = round(llm_eligible_count / max(1, len(ranked)), 4)
            profile_payloads.append(
                {
                    "profile": scenario.key,
                    "label": scenario.label,
                    "profile_text": _clean_text(scenario.profile_text),
                    "top_n": top_n,
                    "top_count": len(ranked),
                    "needs_llm_count": needs_llm_count,
                    "needs_llm_ratio": ratio,
                    "llm_validation_eligible_count": llm_eligible_count,
                    "llm_validation_eligible_ratio": eligible_ratio,
                    "status": _ratio_status(eligible_ratio),
                    "hierarchy_issues": dict(sorted(issue_counts.items())),
                    "needs_llm_rows": needs_llm_rows,
                }
            )

        total_top = sum(item["top_count"] for item in profile_payloads)
        total_needs_llm = sum(item["needs_llm_count"] for item in profile_payloads)
        total_ratio = round(total_needs_llm / max(1, total_top), 4)
        total_llm_eligible = sum(item["llm_validation_eligible_count"] for item in profile_payloads)
        total_eligible_ratio = round(total_llm_eligible / max(1, total_top), 4)
        payload: dict[str, Any] = {
            "model": model_name,
            "source": source_name or "all",
            "candidate_count": len(candidates),
            "rerank_candidate_count": rerank_limit,
            "top": top_n,
            "llm_min_score": llm_min_score,
            "thresholds": {
                "ok_max_ratio": 0.30,
                "watch_max_ratio": 0.50,
                "too_high_above": 0.50,
            },
            "totals": {
                "profiles": len(profile_payloads),
                "top_rows": total_top,
                "needs_llm": total_needs_llm,
                "needs_llm_ratio": total_ratio,
                "llm_validation_eligible": total_llm_eligible,
                "llm_validation_eligible_ratio": total_eligible_ratio,
                "status": _ratio_status(total_eligible_ratio),
                "hierarchy_issues": dict(sorted(global_issues.items())),
            },
            "profiles": profile_payloads,
        }

        output_json = str(options.get("output_json") or "").strip()
        if output_json:
            output_path = Path(output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if bool(options.get("json")):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        totals = payload["totals"]
        self.stdout.write(
            self.style.SUCCESS(
                f"needs_llm audit complete top={top_n} ratio={totals['needs_llm_ratio']} status={totals['status']}"
            )
        )
        for profile in profile_payloads:
            self.stdout.write(
                f"- {profile['label']}: needs_llm={profile['needs_llm_count']}/{profile['top_count']} "
                f"ratio={profile['needs_llm_ratio']} status={profile['status']}"
            )
