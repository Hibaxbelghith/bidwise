from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from ai.embeddings import build_user_embedding_text
from ai.jobbert import (
    build_precomputed_jobbert_scores,
    generate_jobbert_embeddings_batch,
    get_or_build_profile_jobbert_embedding,
    jobbert_model_name,
)
from ai.management.commands.audit_final_recommendations import (
    QUERYSET_FIELDS,
    _build_features,
    _clean_text,
    _float,
)
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import (
    build_recommendation_evidence,
    classify_recommendation_bucket,
    evidence_summary,
    filter_ranked_recommendations,
)
from ai.recommendation_service import rank_opportunities
from ai.user_features import build_user_features
from ai.validation_profiles import VALIDATION_PROFILES
from opportunities.models import Opportunite, StatutOpportunite
from users.models import Profil


BENCHMARK_SOURCE_NAME = "BidWise Recommendation Benchmark"
DEFAULT_CANDIDATE_LIMIT = 1700
DEFAULT_RERANK_CANDIDATES = 120
MIN_MATCH_SCORE = 0.1


def _profile_keys() -> list[str]:
    return [profile.key for profile in VALIDATION_PROFILES]


def _validation_profile_by_key(profile_id: str):
    normalized = str(profile_id or "").strip()
    for profile in VALIDATION_PROFILES:
        if profile.key == normalized:
            return profile
    return None


def _features_from_validation_profile(profile_id: str) -> tuple[dict[str, Any], str, str]:
    scenario = _validation_profile_by_key(profile_id)
    if scenario is None:
        raise CommandError(
            f"Unknown validation profile '{profile_id}'. "
            f"Available profiles: {', '.join(_profile_keys())}"
        )
    options = {
        "roles": scenario.roles,
        "skills": scenario.skills,
        "locations": scenario.locations,
        "experience_level": scenario.experience_level,
        "experience_years": None,
        "work_modes": scenario.work_modes,
        "employment_types": "",
    }
    return _build_features(options, scenario.profile_text), scenario.profile_text, scenario.label


def _features_from_db_profile(profile_id: str) -> tuple[dict[str, Any], str, str, Profil]:
    try:
        profile_pk = int(str(profile_id).strip())
    except (TypeError, ValueError):
        raise CommandError(f"Profile id must be numeric or one of: {', '.join(_profile_keys())}")
    try:
        profile = Profil.objects.get(pk=profile_pk)
    except Profil.DoesNotExist as exc:
        raise CommandError(f"Profile not found: {profile_id}") from exc
    features = build_user_features(profile)
    profile_text = build_user_embedding_text(features) or ""
    label = f"Profil #{profile.pk}"
    return features, profile_text, label, profile


def _families(opportunity: Opportunite) -> list[str]:
    enrichment = ((opportunity.extra_data or {}).get("llm_enrichment") or {})
    families = enrichment.get("business_families") or []
    return [str(item) for item in families if str(item).strip()]


class Command(BaseCommand):
    help = (
        "Quickly test recommendations for one validation profile key or one DB profile id. "
        "Uses existing opportunity JobBERT embeddings, reranks candidates, applies quality gates, "
        "and prints titles plus scores without running the full benchmark."
    )

    def add_arguments(self, parser):
        parser.add_argument("--profile-id", required=True, help="Validation profile key or numeric Profil id.")
        parser.add_argument("--top-k", type=int, default=10)
        parser.add_argument("--candidate-limit", type=int, default=DEFAULT_CANDIDATE_LIMIT)
        parser.add_argument("--rerank-candidates", type=int, default=DEFAULT_RERANK_CANDIDATES)
        parser.add_argument("--source", default="all", help="Optional source name, e.g. 'BidWise Recommendation Benchmark'.")
        parser.add_argument(
            "--exclude-benchmark",
            action="store_true",
            help="Exclude internal benchmark opportunities. By default they are included for validation work.",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--list-profiles", action="store_true")

    def handle(self, *args, **options):
        if bool(options.get("list_profiles")):
            self.stdout.write("\n".join(_profile_keys()))
            return

        profile_id = str(options["profile_id"]).strip()
        top_k = max(1, min(int(options.get("top_k") or 10), 50))
        candidate_limit = max(1, min(int(options.get("candidate_limit") or DEFAULT_CANDIDATE_LIMIT), 5000))
        rerank_limit = max(1, min(int(options.get("rerank_candidates") or DEFAULT_RERANK_CANDIDATES), candidate_limit))
        source_name = str(options.get("source") or "all").strip()
        model_name = jobbert_model_name()

        db_profile = None
        if profile_id.isdigit():
            features, profile_text, label, db_profile = _features_from_db_profile(profile_id)
        else:
            features, profile_text, label = _features_from_validation_profile(profile_id)

        profile_strength = compute_profile_strength(
            db_profile or SimpleNamespace(onboarding_completed=True),
            features,
        )
        profile_semantic_text = build_user_embedding_text(features) or profile_text

        profile_vector = []
        if db_profile is not None:
            profile_vector = get_or_build_profile_jobbert_embedding(db_profile, features)
        if not profile_vector:
            profile_vector = generate_jobbert_embeddings_batch(
                [profile_semantic_text],
                model_name=model_name,
                batch_size=1,
            )[0]
        if not profile_vector:
            raise CommandError("Could not build a JobBERT profile vector.")

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
        if bool(options.get("exclude_benchmark")):
            queryset = queryset.exclude(source__nom__iexact=BENCHMARK_SOURCE_NAME)

        candidates = list(queryset[:candidate_limit])
        if not candidates:
            raise CommandError("No embedded opportunities found for this source/filter.")

        raw_jobbert_scores = build_precomputed_jobbert_scores(profile_vector, candidates)
        if not raw_jobbert_scores:
            raise CommandError("No compatible JobBERT vectors found for selected opportunities.")

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
            top_k=max(top_k, min(rerank_limit, 50)),
            min_score=MIN_MATCH_SCORE,
        )
        ranked = filter_ranked_recommendations(
            ranked,
            features=ranking_features,
            profile_strength=profile_strength,
            limit=top_k,
        )

        rows = []
        for opportunity in ranked:
            evidence = build_recommendation_evidence(ranking_features, opportunity, profile_strength)
            bucket, bucket_reason = classify_recommendation_bucket(
                features=ranking_features,
                opportunity=opportunity,
                evidence=evidence,
            )
            debug = getattr(opportunity, "recommendation_debug", {}) or {}
            rows.append(
                {
                    "id": opportunity.pk,
                    "title": opportunity.titre,
                    "company": opportunity.organisation_nom,
                    "source": getattr(getattr(opportunity, "source", None), "nom", "") or "",
                    "score": _float(getattr(opportunity, "match_score", 0.0)),
                    "jobbert_score": _float(debug.get("jobbert_score")),
                    "semantic_score": _float(getattr(opportunity, "semantic_score", 0.0)),
                    "business_score": _float(getattr(opportunity, "business_score", 0.0)),
                    "bucket": bucket,
                    "bucket_reason": bucket_reason,
                    "confidence": getattr(opportunity, "recommendation_confidence", "LOW"),
                    "families": _families(opportunity),
                    "evidence": evidence_summary(evidence),
                    "reasons": list(getattr(opportunity, "reason", []) or [])[:5],
                }
            )

        payload = {
            "profile_id": profile_id,
            "profile_label": label,
            "model": model_name,
            "candidate_count": len(candidates),
            "rerank_count": len(selected),
            "top_k": top_k,
            "features": {key: value for key, value in features.items() if not key.startswith("_")},
            "profile_text": _clean_text(profile_text),
            "results": rows,
        }
        if bool(options.get("json")):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Profile recommendation test profile={profile_id} label='{label}' "
                f"model={model_name} candidates={len(candidates)} reranked={len(selected)} results={len(rows)}"
            )
        )
        if not rows:
            self.stdout.write("No recommendations passed quality gates.")
            return

        for index, row in enumerate(rows, start=1):
            families = ",".join(row["families"]) if row["families"] else "-"
            self.stdout.write(
                f"{index}. score={row['score']:.4f} jobbert={row['jobbert_score']:.4f} "
                f"business={row['business_score']:.4f} bucket={row['bucket']} "
                f"| #{row['id']} {row['title']} | {row['company']} | families={families}"
            )
            if row["reasons"]:
                self.stdout.write(f"   reasons: {', '.join(row['reasons'])}")
