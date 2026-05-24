from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ai.embeddings import build_profile_embedding_content_hash, get_current_profile_embedding_model
from ai.recommendation_service import rank_opportunities
from ai.retrieval import (
    MAX_SEMANTIC_CANDIDATES,
    retrieve_pgvector_candidates,
    retrieve_recommendation_candidates,
)
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import Utilisateur


VECTOR_DIMENSIONS = 384


def vector_at(index, value=1.0):
    vector = [0.0] * VECTOR_DIMENSIONS
    vector[index] = float(value)
    return vector


class RecommendationPgvectorRetrievalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

    def create_opportunity(self, title, vector, **overrides):
        defaults = {
            "titre": title,
            "description": title,
            "organisation_nom": "BidWise Test",
            "ville": "Tunis",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "source": self.source,
            "skills": ["Python"],
            "embedding_vector": vector,
            "embedding_vector_pg": vector,
            "embedding_model": get_current_profile_embedding_model(),
        }
        defaults.update(overrides)
        return Opportunite.objects.create(**defaults)

    def active_jobs_queryset(self):
        return Opportunite.objects.filter(
            statut=StatutOpportunite.ACTIVE,
            type_opportunite=TypeOpportunite.EMPLOI,
        )

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_retrieval_returns_semantic_candidates(self):
        backend = self.create_opportunity("Backend Django Engineer", vector_at(0))
        self.create_opportunity("Machine Learning Engineer", vector_at(1))

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            1,
            embedding_model=get_current_profile_embedding_model(),
        )

        self.assertEqual([item.id for item in candidates], [backend.id])

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_inactive_jobs_are_excluded(self):
        active = self.create_opportunity("Active Backend", vector_at(0))
        self.create_opportunity(
            "Inactive Backend",
            vector_at(0),
            statut=StatutOpportunite.ARCHIVEE,
        )

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            10,
            embedding_model=get_current_profile_embedding_model(),
        )

        self.assertEqual([item.id for item in candidates], [active.id])

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_missing_embeddings_are_excluded(self):
        valid = self.create_opportunity("Valid Backend", vector_at(0))
        self.create_opportunity(
            "Missing PG embedding",
            vector_at(0),
            embedding_vector_pg=None,
        )
        self.create_opportunity(
            "Missing JSON embedding",
            vector_at(0),
            embedding_vector=None,
        )

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            10,
            embedding_model=get_current_profile_embedding_model(),
        )

        self.assertEqual([item.id for item in candidates], [valid.id])

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_incompatible_json_embedding_dimensions_are_excluded(self):
        valid = self.create_opportunity("Valid Backend", vector_at(0))
        self.create_opportunity(
            "Bad JSON Backend",
            vector_at(0),
            embedding_vector=[1.0, 0.0],
        )

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            10,
            embedding_model=get_current_profile_embedding_model(),
        )

        self.assertEqual([item.id for item in candidates], [valid.id])

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_top_k_limit_is_respected(self):
        self.create_opportunity("Backend 1", vector_at(0), date_publication=date.today())
        self.create_opportunity("Backend 2", vector_at(0), date_publication=date.today() - timedelta(days=1))
        self.create_opportunity("Backend 3", vector_at(0), date_publication=date.today() - timedelta(days=2))

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            2,
            embedding_model=get_current_profile_embedding_model(),
        )

        self.assertEqual(len(candidates), 2)

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_fallback_path_returns_bounded_recent_candidates(self):
        recent = self.create_opportunity("Recent Backend", vector_at(1), date_publication=date.today())
        older = self.create_opportunity("Older Backend", vector_at(0), date_publication=date.today() - timedelta(days=1))

        with patch("ai.retrieval.retrieve_pgvector_candidates", side_effect=RuntimeError("pgvector down")):
            candidates = retrieve_recommendation_candidates(
                vector_at(0),
                self.active_jobs_queryset(),
                1,
                embedding_model=get_current_profile_embedding_model(),
            )

        self.assertEqual([item.id for item in candidates], [recent.id])
        self.assertNotIn(older.id, [item.id for item in candidates])

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_business_reranking_is_still_applied_after_retrieval(self):
        backend = self.create_opportunity(
            "Backend Django Engineer",
            vector_at(0),
            skills=["Python", "Django"],
        )
        self.create_opportunity(
            "Generic Python Job",
            vector_at(0),
            skills=["Python"],
        )

        candidates = retrieve_pgvector_candidates(
            vector_at(0),
            self.active_jobs_queryset(),
            10,
            embedding_model=get_current_profile_embedding_model(),
        )
        ranked = rank_opportunities(
            vector_at(0),
            candidates,
            features={"skills": ["Python", "Django"], "roles": ["Backend Developer"]},
            top_k=1,
        )

        self.assertEqual(ranked[0].id, backend.id)
        self.assertIn("Django", ranked[0].reason)

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
    def test_recommendation_api_uses_pgvector_retrieval_without_regression(self):
        user = Utilisateur.objects.create_user(
            username="pgvector_reco_user",
            email="pgvector_reco_user@example.com",
            password="x",
        )
        profile = user.profil
        profile.competences = ["Python", "Django"]
        profile.target_roles = ["Backend Developer"]
        profile.niveau_experience = "JUNIOR"
        profile.preferred_locations = ["Tunis"]
        profile.remote_preference = "REMOTE"
        profile.employment_types = ["FULL_TIME"]
        profile.opportunity_types = ["JOB"]
        profile.embedding = vector_at(0)
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = VECTOR_DIMENSIONS
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = build_profile_embedding_content_hash(profile)
        profile.embedding_features_hash = profile.embedding_content_hash
        profile.save()

        matched = self.create_opportunity(
            "Backend Django Engineer",
            vector_at(0),
            skills=["Python", "Django"],
        )
        self.create_opportunity(
            "Archived Backend",
            vector_at(0),
            statut=StatutOpportunite.ARCHIVEE,
        )
        self.create_opportunity(
            "Internship Backend",
            vector_at(0),
            type_opportunite=TypeOpportunite.STAGE,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/recommendations/?limit=5")

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data]
        self.assertIn(matched.id, ids)
        self.assertTrue(all(item["type"] == TypeOpportunite.EMPLOI for item in response.data))
        self.assertLessEqual(len(ids), 5)
        self.assertLessEqual(len(ids), MAX_SEMANTIC_CANDIDATES)

    def test_recommendation_api_error_suppresses_recent_fallback_by_default(self):
        user = Utilisateur.objects.create_user(
            username="fallback_job_user",
            email="fallback_job_user@example.com",
            password="x",
        )
        profile = user.profil
        profile.opportunity_types = ["JOB"]
        profile.save(update_fields=["opportunity_types"])

        job = self.create_opportunity(
            "Frontend Developer",
            vector_at(0),
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today() - timedelta(days=1),
        )
        self.create_opportunity(
            "Public Tender",
            vector_at(1),
            type_opportunite=TypeOpportunite.PROJET,
            date_publication=date.today(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        with patch("ai.views._build_recommendations", side_effect=RuntimeError("boom")):
            response = client.get("/api/recommendations/?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    @override_settings(RECOMMENDATION_SHOW_RECENT_FALLBACK=True)
    def test_recommendation_api_flagged_global_fallback_respects_profile_opportunity_types(self):
        user = Utilisateur.objects.create_user(
            username="flagged_fallback_job_user",
            email="flagged_fallback_job_user@example.com",
            password="x",
        )
        profile = user.profil
        profile.opportunity_types = ["JOB"]
        profile.save(update_fields=["opportunity_types"])

        job = self.create_opportunity(
            "Frontend Developer",
            vector_at(0),
            type_opportunite=TypeOpportunite.EMPLOI,
            date_publication=date.today() - timedelta(days=1),
        )
        self.create_opportunity(
            "Public Tender",
            vector_at(1),
            type_opportunite=TypeOpportunite.PROJET,
            date_publication=date.today(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        with patch("ai.views._build_recommendations", side_effect=RuntimeError("boom")):
            response = client.get("/api/recommendations/?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [job.id])
        self.assertTrue(all(item["type"] == TypeOpportunite.EMPLOI for item in response.data))

    def test_recommendation_api_missing_profile_embedding_suppresses_recent_fallback_by_default(self):
        user = Utilisateur.objects.create_user(
            username="missing_embedding_job_user",
            email="missing_embedding_job_user@example.com",
            password="x",
        )
        profile = user.profil
        profile.competences = ["React", "JavaScript", "CSS"]
        profile.target_roles = ["Frontend Developer"]
        profile.niveau_experience = "JUNIOR"
        profile.preferred_locations = ["Tunis"]
        profile.remote_preference = "REMOTE"
        profile.employment_types = ["FULL_TIME"]
        profile.opportunity_types = ["JOB"]
        profile.save()

        job = self.create_opportunity(
            "Frontend Developer",
            vector_at(0),
            type_opportunite=TypeOpportunite.EMPLOI,
            skills=["React", "JavaScript", "CSS"],
            date_publication=date.today() - timedelta(days=1),
        )
        self.create_opportunity(
            "Procurement Project",
            vector_at(1),
            type_opportunite=TypeOpportunite.PROJET,
            date_publication=date.today(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        with patch("ai.embeddings.enqueue_profile_embedding_refresh", return_value=True):
            response = client.get("/api/recommendations/?limit=5")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
