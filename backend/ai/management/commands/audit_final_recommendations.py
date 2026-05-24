from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ai.embeddings import build_user_embedding_text
from ai.jobbert import (
    build_precomputed_jobbert_scores,
    generate_jobbert_embeddings_batch,
    jobbert_model_name,
)
from ai.quality_gates import build_recommendation_evidence, classify_recommendation_bucket
from ai.recommendation_service import rank_opportunities
from opportunities.models import Opportunite, StatutOpportunite


DEFAULT_PROFILE_TEXT = (
    "Role: Frontend developer junior. Skills: React, JavaScript, HTML, CSS, "
    "TypeScript, responsive UI, API integration. Experience: junior, 0 to 2 years. "
    "Location: Tunis. Work mode: on-site or hybrid."
)

QUERYSET_FIELDS = (
    "id",
    "titre",
    "description",
    "organisation_nom",
    "ville",
    "type_opportunite",
    "contract_type",
    "availability",
    "normalized_work_mode",
    "salary",
    "skills",
    "raw_skills",
    "normalized_skills",
    "normalized_industries",
    "languages",
    "experience_min",
    "experience_max",
    "education_level",
    "extra_data",
    "date_publication",
    "jobbert_embedding_vector",
    "jobbert_embedding_model",
    "source__nom",
)


def _clean_text(value, max_chars=1000):
    text = " ".join(str(value or "").split())
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _csv(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _float(value):
    try:
        return round(float(value or 0.0), 4)
    except (TypeError, ValueError):
        return 0.0


def _build_features(options, profile_text):
    roles = _csv(options.get("roles"))
    skills = _csv(options.get("skills"))
    locations = _csv(options.get("locations"))
    work_modes = _csv(options.get("work_modes"))
    employment_types = _csv(options.get("employment_types"))

    features = {
        "roles": roles,
        "target_roles": roles,
        "skills": skills,
        "profile_skills": skills,
        "locations": locations,
        "work_modes": work_modes,
        "employment_types": employment_types,
        "experience_level": str(options.get("experience_level") or "").strip().upper(),
        "resume_text": profile_text,
    }
    if options.get("experience_years") is not None:
        features["experience_years"] = options.get("experience_years")
    return {key: value for key, value in features.items() if value not in ("", [], None)}


class Command(BaseCommand):
    help = (
        "Audit final recommendation ranking: JobBERT retrieval plus BidWise business reranking. "
        "This is non-destructive and uses existing opportunity JobBERT embeddings."
    )

    def add_arguments(self, parser):
        parser.add_argument("--profile-text", default="")
        parser.add_argument("--profile-file", default="")
        parser.add_argument("--source", default="all")
        parser.add_argument("--candidate-limit", type=int, default=1700)
        parser.add_argument("--rerank-candidates", type=int, default=120)
        parser.add_argument("--top", type=int, default=20)
        parser.add_argument("--roles", default="")
        parser.add_argument("--skills", default="")
        parser.add_argument("--locations", default="")
        parser.add_argument("--experience-level", default="")
        parser.add_argument("--experience-years", type=float, default=None)
        parser.add_argument("--work-modes", default="")
        parser.add_argument("--employment-types", default="")
        parser.add_argument("--include-benchmark", action="store_true")
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        profile_text = str(options.get("profile_text") or "").strip()
        profile_file = str(options.get("profile_file") or "").strip()
        if profile_file:
            path = Path(profile_file)
            if not path.exists():
                raise CommandError(f"Profile file not found: {profile_file}")
            profile_text = path.read_text(encoding="utf-8").strip()
        if not profile_text:
            profile_text = DEFAULT_PROFILE_TEXT

        source_name = str(options.get("source") or "all").strip()
        candidate_limit = max(1, min(int(options.get("candidate_limit") or 1700), 5000))
        rerank_limit = max(1, min(int(options.get("rerank_candidates") or 120), candidate_limit))
        top_n = max(1, min(int(options.get("top") or 20), 100))
        model_name = jobbert_model_name()

        features = _build_features(options, profile_text)
        profile_semantic_text = build_user_embedding_text(features) or profile_text
        profile_vector = generate_jobbert_embeddings_batch(
            [profile_semantic_text],
            model_name=model_name,
            batch_size=1,
        )[0]

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
            queryset = queryset.exclude(source__nom__iexact="BidWise Recommendation Benchmark")

        candidates = list(queryset[:candidate_limit])
        if not candidates:
            raise CommandError("No JobBERT-embedded candidates found. Generate opportunity embeddings first.")

        raw_jobbert_scores = build_precomputed_jobbert_scores(profile_vector, candidates)
        if not raw_jobbert_scores:
            raise CommandError("No compatible JobBERT vectors found for the selected candidates.")

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

        rows = []
        for opportunity in ranked:
            debug = getattr(opportunity, "recommendation_debug", {}) or {}
            evidence = build_recommendation_evidence(ranking_features, opportunity)
            bucket, bucket_reason = classify_recommendation_bucket(
                features=ranking_features,
                opportunity=opportunity,
                evidence=evidence,
            )
            rows.append(
                {
                    "id": opportunity.pk,
                    "title": opportunity.titre,
                    "company": opportunity.organisation_nom,
                    "location": opportunity.ville,
                    "source": getattr(getattr(opportunity, "source", None), "nom", "") or "",
                    "skills": list(opportunity.skills or [])[:8],
                    "final_score": _float(getattr(opportunity, "match_score", 0.0)),
                    "jobbert_score": _float(debug.get("jobbert_score")),
                    "business_score": _float(getattr(opportunity, "business_score", 0.0)),
                    "experience_gap_penalty": _float(debug.get("experience_gap_penalty")),
                    "hierarchy_validation": debug.get("hierarchy_validation", {}),
                    "llm_family_penalty": _float(debug.get("llm_business_family_mismatch_penalty")),
                    "recommendation_bucket": bucket,
                    "recommendation_bucket_reason": bucket_reason,
                    "reasons": list(getattr(opportunity, "reason", []) or [])[:5],
                    "business_components": debug.get("business_components", {}),
                }
            )

        payload = {
            "model": model_name,
            "source": source_name or "all",
            "candidate_count": len(candidates),
            "rerank_candidate_count": len(selected),
            "profile_text": _clean_text(profile_text),
            "profile_semantic_text": _clean_text(profile_semantic_text),
            "features": {
                key: value
                for key, value in features.items()
                if not key.startswith("_")
            },
            "top": rows,
        }
        if bool(options.get("json")):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Final recommendation audit model={model_name} candidates={len(candidates)} "
                f"reranked={len(selected)}"
            )
        )
        for index, row in enumerate(rows, start=1):
            self.stdout.write(
                f"{index}. final={row['final_score']:.4f} jobbert={row['jobbert_score']:.4f} "
                f"business={row['business_score']:.4f} | {row['title']} | {row['company']} | "
                f"{row['location']} | {row['source']}"
            )
            if row["reasons"]:
                self.stdout.write(f"   reasons: {', '.join(row['reasons'])}")
