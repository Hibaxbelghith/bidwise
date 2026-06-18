from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
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
from ai.hierarchy_llm import (
    LLMHierarchyValidation,
    build_opportunity_content_hash,
    build_hierarchy_validation_cache_key,
    get_cached_hierarchy_decision,
    store_hierarchy_decision,
    validate_hierarchy_with_llm,
)
from ai.llm.providers import LLMProviderError, LLMProviderUnavailable, LLMTransientProviderError
from ai.quality_gates import (
    BUCKET_RELATED_REVIEW,
    BUCKET_STRONG_MATCH,
    build_recommendation_evidence,
    classify_recommendation_bucket,
)
from ai.recommendation_service import rank_opportunities, select_source_balanced_candidates
from ai.validation_profiles import VALIDATION_PROFILES
from opportunities.models import Opportunite, StatutOpportunite


BENCHMARK_SOURCE_NAME = "BidWise Recommendation Benchmark"
LLM_MIN_CONFIDENCE = 0.65
LLM_VALIDATION_MIN_SCORE = 0.60


@dataclass(frozen=True)
class ProfileScenario:
    key: str
    label: str
    profile_text: str
    roles: str
    skills: str
    locations: str
    experience_level: str
    work_modes: str = ""


DEFAULT_SCENARIOS = (
    ProfileScenario(
        key="comptable_junior",
        label="Comptable junior",
        profile_text=(
            "Role: Comptable junior. Skills: comptabilité, MS Office, gestion, audit, fiscalité, français. "
            "Experience: junior, 1 à 2 ans. Location: Tunis or Ariana. Education: CCA or Bac+3."
        ),
        roles="Comptable",
        skills="comptabilité,MS Office,gestion,audit,fiscalité,français",
        locations="Tunis,Ariana",
        experience_level="JUNIOR",
    ),
    ProfileScenario(
        key="production_team_lead",
        label="Chef d'équipe production",
        profile_text=(
            "Role: Chef d'équipe production. Skills: contrôle qualité, traçabilité, process industriel, "
            "production agroalimentaire, organisation, gestion équipe. Experience: confirmé, 2 à 4 ans. "
            "Location: Ben Arous. Education: Bac+3. Work mode: on-site."
        ),
        roles="Chef d'équipe production",
        skills="contrôle qualité,traçabilité,process industriel,production agroalimentaire,organisation,gestion équipe",
        locations="Ben Arous",
        experience_level="CONFIRME",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="civil_engineer_junior",
        label="Ingénieur génie civil travaux",
        profile_text=(
            "Role: Ingénieur génie civil travaux. Skills: Autocad, MS Project, contrôle qualité, planning chantier, "
            "supervision travaux, études de terrain. Experience: junior, 1 à 3 ans. Location: Ben Arous or Tunis. "
            "Education: Bac+5. Work mode: on-site."
        ),
        roles="Ingénieur génie civil travaux",
        skills="Autocad,MS Project,contrôle qualité,planning chantier,supervision travaux,études de terrain",
        locations="Ben Arous,Tunis",
        experience_level="JUNIOR",
        work_modes="ON_SITE",
    ),
    ProfileScenario(
        key="it_helpdesk",
        label="IT Helpdesk Officer",
        profile_text=(
            "Role: IT Helpdesk Officer. Skills: support helpdesk, Windows, Microsoft 365, Active Directory, réseau, "
            "installation hardware software, troubleshooting. Experience: junior, 1 à 3 ans. Location: Tunis. "
            "Education: Bac+3."
        ),
        roles="IT Helpdesk Officer,Support IT,Technicien support informatique",
        skills="support helpdesk,Windows,Microsoft 365,Active Directory,réseau,installation hardware software,troubleshooting",
        locations="Tunis",
        experience_level="JUNIOR",
    ),
)

DEFAULT_SCENARIOS = VALIDATION_PROFILES


def _scenario_options(scenario: ProfileScenario) -> dict[str, Any]:
    return {
        "profile_text": scenario.profile_text,
        "roles": scenario.roles,
        "skills": scenario.skills,
        "locations": scenario.locations,
        "experience_level": scenario.experience_level,
        "work_modes": scenario.work_modes,
        "employment_types": "",
        "experience_years": None,
    }


def _issue_name(row: dict[str, Any]) -> str:
    validation = row.get("hierarchy_validation") or {}
    if not isinstance(validation, dict):
        return "none"
    issue = str(validation.get("hierarchy_issue") or "none")
    if issue != "none":
        return issue
    if validation.get("needs_llm"):
        return "needs_llm"
    return "none"


def _compact_row(opportunity, bucket: str, bucket_reason: str) -> dict[str, Any]:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {})
    llm_validation = debug.get("llm_hierarchy_validation", {})
    llm_policy = debug.get("llm_hierarchy_policy", {})
    return {
        "id": opportunity.pk,
        "title": opportunity.titre,
        "company": opportunity.organisation_nom,
        "location": opportunity.ville,
        "source": getattr(getattr(opportunity, "source", None), "nom", "") or "",
        "final_score": _float(getattr(opportunity, "match_score", 0.0)),
        "jobbert_score": _float(debug.get("jobbert_score")),
        "bucket": bucket,
        "bucket_reason": bucket_reason,
        "needs_llm": bool((validation or {}).get("needs_llm")) if isinstance(validation, dict) else False,
        "hierarchy_issue": _issue_name({"hierarchy_validation": validation}),
        "llm_hierarchy_validation": llm_validation if isinstance(llm_validation, dict) else {},
        "llm_hierarchy_policy": llm_policy if isinstance(llm_policy, dict) else {},
        "llm_overridden_by_exact_evidence": bool(
            isinstance(llm_policy, dict) and llm_policy.get("overridden_by_exact_evidence")
        ),
        "reasons": list(getattr(opportunity, "reason", []) or [])[:5],
    }


def _should_validate_llm_hierarchy(
    opportunity,
    bucket: str,
    *,
    min_score: float = LLM_VALIDATION_MIN_SCORE,
) -> bool:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
    if not isinstance(validation, dict) or not validation.get("needs_llm"):
        return False
    return bucket == BUCKET_STRONG_MATCH or _float(getattr(opportunity, "match_score", 0.0)) >= min_score


def _opportunity_skills(opportunity) -> list[str]:
    skills = getattr(opportunity, "skills", None) or []
    if isinstance(skills, list):
        return [str(skill).strip() for skill in skills if str(skill or "").strip()]
    return []


def _llm_issue_has_explicit_opportunity_support(
    validation: dict[str, Any],
    result: LLMHierarchyValidation,
) -> bool:
    opportunity_signal = validation.get("opportunity_signal") or {}
    if not isinstance(opportunity_signal, dict):
        opportunity_signal = {}

    if result.issue == "seniority_gap":
        return bool(opportunity_signal.get("seniority_terms"))
    if result.issue == "responsibility_gap":
        return bool(opportunity_signal.get("responsibility_terms"))
    if result.issue in {"qualification_gap", "overqualified_scope"}:
        return bool(opportunity_signal.get("qualification_terms"))
    return result.issue not in {"none", "unclear"}


def _exact_match_should_survive_llm_review(
    *,
    features: dict[str, Any] | None,
    opportunity,
    result: LLMHierarchyValidation,
) -> bool:
    if result.is_compatible or result.issue not in {"seniority_gap", "responsibility_gap"}:
        return False
    evidence = build_recommendation_evidence(features or {}, opportunity)
    try:
        score = float(getattr(opportunity, "match_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return bool(
        evidence.get("role_match")
        and int(evidence.get("skill_overlap") or 0) >= 2
        and score >= 0.75
    )


def _apply_llm_hierarchy_result(
    opportunity,
    result: LLMHierarchyValidation,
    *,
    features: dict[str, Any] | None = None,
) -> None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    if not isinstance(debug, dict):
        debug = {}
    validation = dict(debug.get("hierarchy_validation") or {})
    debug["llm_hierarchy_validation"] = result.as_dict()
    debug["llm_hierarchy_policy"] = {
        "applied": False,
        "overridden_by_exact_evidence": False,
        "kept_for_review": False,
        "reason": "",
    }

    if _exact_match_should_survive_llm_review(
        features=features,
        opportunity=opportunity,
        result=result,
    ):
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = "none"
        validation["score_multiplier"] = 1.0
        validation["reason"] = "Exact role and skill evidence override weak LLM hierarchy concern"
        debug["llm_hierarchy_policy"] = {
            "applied": False,
            "overridden_by_exact_evidence": True,
            "kept_for_review": False,
            "reason": validation["reason"],
        }
    elif (
        result.confidence < LLM_MIN_CONFIDENCE
        or result.issue == "unclear"
        or (not result.is_compatible and not _llm_issue_has_explicit_opportunity_support(validation, result))
    ):
        validation["needs_llm"] = True
        validation["hierarchy_issue"] = "none"
        validation["reason"] = result.reason or "LLM hierarchy validation remains unsupported by explicit terms"
        debug["llm_hierarchy_policy"] = {
            "applied": False,
            "overridden_by_exact_evidence": False,
            "kept_for_review": True,
            "reason": validation["reason"],
        }
    elif result.is_compatible:
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = "none"
        validation["score_multiplier"] = 1.0
        validation["reason"] = result.reason or "LLM confirmed hierarchy compatibility"
        debug["llm_hierarchy_policy"] = {
            "applied": True,
            "overridden_by_exact_evidence": False,
            "kept_for_review": False,
            "reason": validation["reason"],
        }
    else:
        validation["needs_llm"] = False
        validation["hierarchy_issue"] = result.issue if result.issue != "none" else "unclear"
        validation["score_multiplier"] = min(float(validation.get("score_multiplier") or 1.0), 0.64)
        validation["reason"] = result.reason or "LLM rejected hierarchy compatibility"
        debug["llm_hierarchy_policy"] = {
            "applied": True,
            "overridden_by_exact_evidence": False,
            "kept_for_review": False,
            "reason": validation["reason"],
        }

    debug["hierarchy_validation"] = validation
    setattr(opportunity, "recommendation_debug", debug)


def _validate_llm_hierarchy_if_needed(
    *,
    scenario: ProfileScenario,
    opportunity,
    cache: dict[str, LLMHierarchyValidation],
    features: dict[str, Any] | None = None,
) -> LLMHierarchyValidation | None:
    debug = getattr(opportunity, "recommendation_debug", {}) or {}
    validation = debug.get("hierarchy_validation", {}) if isinstance(debug, dict) else {}
    if not isinstance(validation, dict) or not validation.get("needs_llm"):
        return None

    opportunity_skills = _opportunity_skills(opportunity)
    opportunity_content_hash = build_opportunity_content_hash(
        opportunity_title=str(getattr(opportunity, "titre", "") or ""),
        opportunity_description=str(getattr(opportunity, "description", "") or ""),
        opportunity_skills=opportunity_skills,
    )
    cache_key = build_hierarchy_validation_cache_key(
        profile_text=scenario.profile_text,
        opportunity_id=getattr(opportunity, "id", ""),
        hierarchy_validation=validation,
        opportunity_content_hash=opportunity_content_hash,
    )
    result = cache.get(cache_key)
    if result is None:
        result = get_cached_hierarchy_decision(cache_key)
    if result is None:
        result = validate_hierarchy_with_llm(
            profile_text=scenario.profile_text,
            opportunity_id=getattr(opportunity, "id", ""),
            opportunity_title=str(getattr(opportunity, "titre", "") or ""),
            opportunity_description=str(getattr(opportunity, "description", "") or ""),
            opportunity_skills=opportunity_skills,
            hierarchy_validation=validation,
        )
        store_hierarchy_decision(
            cache_key=cache_key,
            profile_text=scenario.profile_text,
            opportunity_id=getattr(opportunity, "id", ""),
            opportunity_content_hash=opportunity_content_hash,
            hierarchy_validation=validation,
            result=result,
        )
        cache[cache_key] = result
    else:
        cache[cache_key] = result
    _apply_llm_hierarchy_result(opportunity, result, features=features)
    return result


class Command(BaseCommand):
    help = "Run the final recommendation engine against the curated BidWise validation profiles."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="all")
        parser.add_argument("--candidate-limit", type=int, default=1700)
        parser.add_argument("--rerank-candidates", type=int, default=120)
        parser.add_argument("--top", type=int, default=15)
        parser.add_argument("--include-benchmark", action="store_true")
        parser.add_argument(
            "--profiles",
            default="all",
            help="Comma-separated scenario keys, or 'all'.",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument(
            "--use-llm-validation",
            action="store_true",
            help="Validate only hierarchy needs_llm=true rows with the configured LLM provider.",
        )
        parser.add_argument(
            "--llm-min-score",
            type=float,
            default=LLM_VALIDATION_MIN_SCORE,
            help="Minimum final score for validating RELATED_REVIEW needs_llm rows.",
        )
        parser.add_argument(
            "--output-json",
            default="",
            help="Optional path where the benchmark JSON payload will be written.",
        )

    def handle(self, *args, **options):
        model_name = jobbert_model_name()
        source_name = str(options.get("source") or "all").strip()
        candidate_limit = max(1, min(int(options.get("candidate_limit") or 1700), 5000))
        rerank_limit = max(1, min(int(options.get("rerank_candidates") or 120), candidate_limit))
        top_n = max(1, min(int(options.get("top") or 15), 100))
        use_llm_validation = bool(options.get("use_llm_validation"))
        llm_min_score = max(0.0, min(float(options.get("llm_min_score") or LLM_VALIDATION_MIN_SCORE), 1.0))
        llm_cache: dict[str, LLMHierarchyValidation] = {}
        requested_profiles = {
            item.strip()
            for item in str(options.get("profiles") or "all").split(",")
            if item.strip()
        }
        scenarios = [
            scenario
            for scenario in DEFAULT_SCENARIOS
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
        for scenario in scenarios:
            scenario_options = _scenario_options(scenario)
            features = _build_features(scenario_options, scenario.profile_text)
            profile_semantic_text = build_user_embedding_text(features) or scenario.profile_text
            profile_vector = generate_jobbert_embeddings_batch(
                [profile_semantic_text],
                model_name=model_name,
                batch_size=1,
            )[0]
            raw_jobbert_scores = build_precomputed_jobbert_scores(profile_vector, candidates)
            if not raw_jobbert_scores:
                raise CommandError(f"No compatible JobBERT vectors for profile: {scenario.key}")

            selected = select_source_balanced_candidates(candidates, raw_jobbert_scores, rerank_limit)
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

            rows = []
            bucket_counts = Counter()
            issue_counts = Counter()
            needs_llm_count = 0
            llm_validated_count = 0
            llm_error_count = 0
            llm_eligible_count = 0
            llm_override_count = 0
            for opportunity in ranked:
                evidence = build_recommendation_evidence(ranking_features, opportunity)
                bucket, bucket_reason = classify_recommendation_bucket(
                    features=ranking_features,
                    opportunity=opportunity,
                    evidence=evidence,
                )
                llm_eligible = _should_validate_llm_hierarchy(
                    opportunity,
                    bucket,
                    min_score=llm_min_score,
                )
                if llm_eligible:
                    llm_eligible_count += 1

                if use_llm_validation and llm_eligible:
                    try:
                        llm_result = _validate_llm_hierarchy_if_needed(
                            scenario=scenario,
                            opportunity=opportunity,
                            cache=llm_cache,
                            features=ranking_features,
                        )
                        if llm_result is not None:
                            llm_validated_count += 1
                    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
                        llm_error_count += 1
                        debug = getattr(opportunity, "recommendation_debug", {}) or {}
                        if isinstance(debug, dict):
                            debug["llm_hierarchy_validation_error"] = str(exc)
                            setattr(opportunity, "recommendation_debug", debug)

                    evidence = build_recommendation_evidence(ranking_features, opportunity)
                    bucket, bucket_reason = classify_recommendation_bucket(
                        features=ranking_features,
                        opportunity=opportunity,
                        evidence=evidence,
                    )
                row = _compact_row(opportunity, bucket, bucket_reason)
                row["llm_validation_eligible"] = llm_eligible
                rows.append(row)
                bucket_counts[bucket] += 1
                issue_counts[row["hierarchy_issue"]] += 1
                if row["needs_llm"]:
                    needs_llm_count += 1
                if row["llm_overridden_by_exact_evidence"]:
                    llm_override_count += 1

            profile_payloads.append(
                {
                    "profile": scenario.key,
                    "label": scenario.label,
                    "profile_text": _clean_text(scenario.profile_text),
                    "summary": {
                        "top_count": len(rows),
                        "strong_match": bucket_counts[BUCKET_STRONG_MATCH],
                        "related_review": bucket_counts[BUCKET_RELATED_REVIEW],
                        "needs_llm": needs_llm_count,
                        "llm_validation_eligible": llm_eligible_count,
                        "llm_validated": llm_validated_count,
                        "llm_errors": llm_error_count,
                        "llm_overridden_by_exact_evidence": llm_override_count,
                        "hierarchy_issues": dict(sorted(issue_counts.items())),
                        "top_strong_titles": [
                            row["title"] for row in rows if row["bucket"] == BUCKET_STRONG_MATCH
                        ][:5],
                    },
                    "top": rows,
                }
            )

        totals = {
            "profiles": len(profile_payloads),
            "top_rows": sum(profile["summary"]["top_count"] for profile in profile_payloads),
            "strong_match": sum(profile["summary"]["strong_match"] for profile in profile_payloads),
            "related_review": sum(profile["summary"]["related_review"] for profile in profile_payloads),
            "needs_llm": sum(profile["summary"]["needs_llm"] for profile in profile_payloads),
            "llm_validation_eligible": sum(
                profile["summary"].get("llm_validation_eligible", 0) for profile in profile_payloads
            ),
            "llm_validated": sum(profile["summary"].get("llm_validated", 0) for profile in profile_payloads),
            "llm_errors": sum(profile["summary"].get("llm_errors", 0) for profile in profile_payloads),
            "llm_overridden_by_exact_evidence": sum(
                profile["summary"].get("llm_overridden_by_exact_evidence", 0)
                for profile in profile_payloads
            ),
        }
        payload = {
            "model": model_name,
            "source": source_name or "all",
            "use_llm_validation": use_llm_validation,
            "candidate_count": len(candidates),
            "rerank_candidate_count": rerank_limit,
            "top": top_n,
            "totals": totals,
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Final recommendation profile benchmark complete model={model_name} candidates={len(candidates)}"
            )
        )
        self.stdout.write(
            f"Totals: profiles={totals['profiles']} strong={totals['strong_match']} "
            f"review={totals['related_review']} needs_llm={totals['needs_llm']} "
            f"llm_validated={totals['llm_validated']} llm_errors={totals['llm_errors']} "
            f"llm_overrides={totals['llm_overridden_by_exact_evidence']}"
        )
        for profile in profile_payloads:
            summary = profile["summary"]
            self.stdout.write(
                f"- {profile['label']}: strong={summary['strong_match']} "
                f"review={summary['related_review']} needs_llm={summary['needs_llm']} "
                f"llm_validated={summary['llm_validated']} llm_errors={summary['llm_errors']}"
            )
            if summary["top_strong_titles"]:
                self.stdout.write("  strong: " + " | ".join(summary["top_strong_titles"]))
