from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from ai.embeddings import (
    build_user_embedding,
    build_user_features_hash,
    get_cached_profile_embedding_or_enqueue,
    profile_embedding_has_semantic_content,
    store_profile_embedding,
)
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import fallback_limit_for_profile, filter_ranked_recommendations
from ai.crossencoder import rerank_ranked_opportunities
from ai.recommendation_service import rank_opportunities
from ai.retrieval import MAX_SEMANTIC_CANDIDATES, retrieve_recommendation_candidates
from ai.user_features import build_user_features
from ai.views import (
    MIN_MATCH_SCORE,
    BUSINESS_RERANK_CANDIDATES,
    _profile_completion_state,
    _profile_opportunity_types,
    _serialize_fallback,
    _serialize_recommendation,
)
from opportunities.embeddings.service import build_embedding_model_identifier, generate_embeddings_batch
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from opportunities.nlp.nlp_preprocessing import prepare_combined_text
from users.models import ProfileResume, Utilisateur
from users.resume_semantic.service import process_profile_resume_semantics

from .dataset import BenchmarkDataset, BenchmarkProfile


BENCHMARK_SOURCE_NAME = "BidWise Recommendation Benchmark"
BENCHMARK_SOURCE_URL = "https://benchmark.bidwise.local/recommendations"
BENCHMARK_USER_DOMAIN = "benchmark.bidwise.local"


@dataclass(frozen=True)
class FixtureState:
    users_by_profile_id: dict[str, Utilisateur]
    opportunity_count: int
    embedding_model: str


PROFILE_FIELD_DEFAULTS = {
    "competences": [],
    "domaines_interet": [],
    "target_roles": [],
    "niveau_experience": "",
    "annees_experience": None,
    "opportunity_types": ["JOB"],
    "preferred_locations": [],
    "remote_preference": "",
    "work_mode_preferences": [],
    "compensation_expectation": None,
    "compensation_currency": "TND",
    "compensation_period": "",
    "employment_types": [],
    "onboarding_completed": False,
    "last_onboarding_step": None,
}


def _benchmark_username(profile_id: str) -> str:
    safe = profile_id.replace("-", "_").replace(".", "_")
    return f"benchmark_{safe}"


def _to_pgvector_payload(vector: list[float] | None) -> list[float] | None:
    if not isinstance(vector, list) or not vector:
        return None
    expected_dimensions = int(getattr(settings, "OPPORTUNITY_PGVECTOR_DIMENSIONS", 384) or 384)
    if len(vector) != expected_dimensions:
        return None
    values = []
    for item in vector:
        try:
            value = float(item)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        values.append(value)
    return values


def _has_valid_vector_payload(vector: Any) -> bool:
    if vector is None:
        return False
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    if isinstance(vector, tuple):
        vector = list(vector)
    if not isinstance(vector, list):
        return False
    return _to_pgvector_payload(vector) is not None


def _fixture_date(index: int) -> date:
    return date(2026, 5, 1) - timedelta(days=index % 17)


class DjangoBenchmarkFixtureBuilder:
    """Creates deterministic benchmark-owned rows without changing recommender logic."""

    def __init__(self) -> None:
        self._source: SourceOpportunite | None = None

    @property
    def source(self) -> SourceOpportunite:
        if self._source is None:
            self._source, _ = SourceOpportunite.objects.update_or_create(
                nom=BENCHMARK_SOURCE_NAME,
                defaults={
                    "url": BENCHMARK_SOURCE_URL,
                    "type_source": "SITE_EMPLOI",
                },
            )
        return self._source

    def ensure_fixtures(
        self,
        dataset: BenchmarkDataset,
        *,
        rebuild_embeddings: bool = False,
        batch_size: int = 32,
    ) -> FixtureState:
        users = self._ensure_users(dataset)
        opportunity_count = self._ensure_opportunities(
            dataset,
            rebuild_embeddings=rebuild_embeddings,
            batch_size=batch_size,
        )
        return FixtureState(
            users_by_profile_id=users,
            opportunity_count=opportunity_count,
            embedding_model=build_embedding_model_identifier(),
        )

    def prepare_profile_scenario(
        self,
        profile_spec: BenchmarkProfile,
        *,
        resume_text: str | None,
    ) -> Utilisateur:
        user = self._ensure_user(profile_spec)
        profile = user.profil
        fields = dict(PROFILE_FIELD_DEFAULTS)
        fields.update(profile_spec.fields)
        for field_name, value in fields.items():
            setattr(profile, field_name, value)
        profile.save()

        ProfileResume.objects.filter(profile=profile).delete()
        if resume_text:
            resume = ProfileResume.objects.create(
                profile=profile,
                parsed_text=resume_text,
                resume_text_embedding_source=resume_text,
                parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
                parsed_at=timezone.now(),
                source_type=ProfileResume.SourceType.BUILDER,
                metadata={"benchmark": True, "profile_id": profile_spec.profile_id},
                is_active=True,
            )
            process_profile_resume_semantics(resume)

        self._refresh_profile_embedding(profile)
        return user

    def execute_recommendations(self, user: Utilisateur, limit: int) -> list[dict[str, Any]]:
        """Run the existing retrieval/rerank/gating stack against benchmark fixtures only."""
        profile = user.profil
        features = build_user_features(profile)
        profile_strength = compute_profile_strength(profile, features)
        recommendation_mode = "SPARSE_PROFILE" if profile_strength.get("level") == "LOW" else "STANDARD"
        opportunity_types = _profile_opportunity_types(profile)
        user_embedding = get_cached_profile_embedding_or_enqueue(profile)

        queryset = (
            Opportunite.objects
            .filter(source=self.source, statut=StatutOpportunite.ACTIVE)
            .annotate(application_count=Count("candidatures"))
            .order_by("-date_publication", "-id")
        )
        if opportunity_types:
            queryset = queryset.filter(type_opportunite__in=opportunity_types)

        candidate_limit = MAX_SEMANTIC_CANDIDATES
        candidates = retrieve_recommendation_candidates(
            user_embedding,
            queryset,
            candidate_limit,
            embedding_model=getattr(profile, "embedding_model", ""),
        )
        ranked = rank_opportunities(
            user_embedding,
            candidates,
            features=features,
            feedback={"applied_embeddings": [], "applied_skills": []},
            mode=_profile_completion_state(profile),
            top_k=min(candidate_limit, max(int(limit), BUSINESS_RERANK_CANDIDATES)),
            min_score=MIN_MATCH_SCORE,
        )
        ranked = rerank_ranked_opportunities(ranked, features=features)
        ranked = filter_ranked_recommendations(
            ranked,
            features=features,
            profile_strength=profile_strength,
            limit=int(limit),
        )
        if ranked:
            return [
                _serialize_recommendation(item, features=features, profile_strength=profile_strength)
                for item in ranked
            ]

        fallback_limit = fallback_limit_for_profile(int(limit), profile_strength)
        fallback_items = queryset.order_by("-application_count", "-date_publication", "-id")[:fallback_limit]
        return [
            _serialize_fallback(
                item,
                profile_strength=profile_strength,
                recommendation_mode=recommendation_mode,
            )
            for item in fallback_items
        ]

    def _ensure_users(self, dataset: BenchmarkDataset) -> dict[str, Utilisateur]:
        return {profile.profile_id: self._ensure_user(profile) for profile in dataset.profiles}

    def _ensure_user(self, profile_spec: BenchmarkProfile) -> Utilisateur:
        username = _benchmark_username(profile_spec.profile_id)
        user, created = Utilisateur.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{profile_spec.profile_id}@{BENCHMARK_USER_DOMAIN}",
                "first_name": "Benchmark",
                "last_name": profile_spec.profile_id,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        return user

    def _ensure_opportunities(
        self,
        dataset: BenchmarkDataset,
        *,
        rebuild_embeddings: bool,
        batch_size: int,
    ) -> int:
        model_identifier = build_embedding_model_identifier()
        source = self.source
        source_urls = []
        opportunities = []
        for index, item in enumerate(dataset.opportunities):
            source_item_url = f"{BENCHMARK_SOURCE_URL}/{item.opportunity_id}"
            source_urls.append(source_item_url)
            defaults = {
                "titre": item.title,
                "description": item.description,
                "organisation_nom": item.company,
                "ville": item.location,
                "contract_type": item.contract_type,
                "availability": item.availability,
                "normalized_work_mode": "REMOTE" if item.availability.lower() == "remote" else "HYBRID",
                "normalized_contract_types": ["FULL_TIME"],
                "normalized_industries": list(item.industries),
                "experience_min": item.experience_min,
                "experience_max": item.experience_max,
                "skills": list(item.skills),
                "languages": [item.language],
                "type_opportunite": item.type_opportunite,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": _fixture_date(index),
                "external_id": f"benchmark:{item.opportunity_id}",
                "extra_data": {
                    "benchmark": True,
                    "benchmark_opportunity_id": item.opportunity_id,
                    "confusing": item.confusing,
                },
            }
            opportunity, _ = Opportunite.objects.update_or_create(
                source=source,
                source_item_url=source_item_url,
                defaults=defaults,
            )
            opportunities.append(opportunity)

        Opportunite.objects.filter(source=source).exclude(source_item_url__in=source_urls).update(
            statut=StatutOpportunite.ARCHIVEE
        )

        missing_embeddings = [
            opportunity for opportunity in opportunities
            if rebuild_embeddings
            or not _has_valid_vector_payload(opportunity.embedding_vector)
            or not _has_valid_vector_payload(opportunity.embedding_vector_pg)
            or opportunity.embedding_model != model_identifier
        ]
        if missing_embeddings:
            texts = [prepare_combined_text(opportunity) for opportunity in missing_embeddings]
            vectors = generate_embeddings_batch(texts, batch_size=max(1, int(batch_size or 32)))
            rows_to_update = []
            for opportunity, vector in zip(missing_embeddings, vectors):
                opportunity.embedding_vector = vector
                opportunity.embedding_vector_pg = _to_pgvector_payload(vector)
                opportunity.embedding_model = model_identifier
                rows_to_update.append(opportunity)
            if rows_to_update:
                Opportunite.objects.bulk_update(
                    rows_to_update,
                    fields=["embedding_vector", "embedding_vector_pg", "embedding_model"],
                    batch_size=max(1, int(batch_size or 32)),
                )
        return len(opportunities)

    def _refresh_profile_embedding(self, profile: Any) -> None:
        features = build_user_features(profile)
        if not profile_embedding_has_semantic_content(features):
            profile.embedding = None
            profile.embedding_features_hash = ""
            profile.last_embedding_update = None
            profile.embedding_model = ""
            profile.embedding_dimensions = None
            profile.embedding_updated_at = None
            profile.embedding_content_hash = ""
            profile.save(
                update_fields=[
                    "embedding",
                    "embedding_features_hash",
                    "last_embedding_update",
                    "embedding_model",
                    "embedding_dimensions",
                    "embedding_updated_at",
                    "embedding_content_hash",
                ]
            )
            return

        vector = build_user_embedding(features)
        if not vector:
            return
        store_profile_embedding(
            profile,
            vector,
            content_hash=build_user_features_hash(features),
            updated_at=timezone.now(),
        )
