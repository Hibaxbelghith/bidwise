from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ai.embeddings import build_profile_embedding_content_hash, get_current_profile_embedding_model
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    build_recommendation_evidence,
    compute_recommendation_confidence,
    passes_recommendation_quality_gate,
)
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import ProfileResume, Utilisateur


VECTOR_DIMENSIONS = 384


def vector_with_similarity(similarity):
    vector = [0.0] * VECTOR_DIMENSIONS
    vector[0] = float(similarity)
    vector[1] = max(0.0, 1.0 - float(similarity) ** 2) ** 0.5
    return vector


def user_vector():
    return vector_with_similarity(1.0)


@override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=VECTOR_DIMENSIONS)
class RecommendationQualityGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.source = SourceOpportunite.objects.create(
            nom="QualityGateSource",
            url="https://example.com",
            type_source="SITE_EMPLOI",
        )

    def create_user(self, email, **profile_fields):
        user = Utilisateur.objects.create_user(username=email, email=email, password="x")
        profile = user.profil
        for field, value in profile_fields.items():
            setattr(profile, field, value)
        profile.embedding = user_vector()
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = VECTOR_DIMENSIONS
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = build_profile_embedding_content_hash(profile)
        profile.embedding_features_hash = profile.embedding_content_hash
        profile.save()
        return user

    def create_opportunity(self, title, similarity, **overrides):
        defaults = {
            "titre": title,
            "description": title,
            "organisation_nom": "BidWise Test",
            "ville": "Tunis",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "source": self.source,
            "skills": [],
            "embedding_vector": vector_with_similarity(similarity),
            "embedding_vector_pg": vector_with_similarity(similarity),
            "embedding_model": get_current_profile_embedding_model(),
        }
        defaults.update(overrides)
        return Opportunite.objects.create(**defaults)

    def get_recommendations(self, user, limit=10):
        client = APIClient()
        client.force_authenticate(user=user)
        return client.get(f"/api/recommendations/?limit={limit}")

    def test_sparse_python_profile_does_not_recommend_hr_hospitality_or_accounting(self):
        user = self.create_user(
            "python_sparse@example.com",
            competences=["Python"],
            niveau_experience="JUNIOR",
            opportunity_types=["JOB"],
        )
        python_job = self.create_opportunity(
            "Python Developer",
            0.50,
            skills=["Python"],
            date_publication=date.today() - timedelta(days=2),
        )
        self.create_opportunity(
            "Adjoint Ressources Humaines",
            0.44,
            skills=["Excel"],
            experience_min=1,
            experience_max=2,
        )
        self.create_opportunity(
            "Chef Patissiere Junior",
            0.42,
            skills=["Hôtellerie", "Qualité"],
            experience_min=1,
            experience_max=2,
        )
        self.create_opportunity(
            "Accounting Assistant",
            0.43,
            skills=["Excel", "Finance"],
            experience_min=1,
            experience_max=2,
        )

        response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data]
        self.assertIn(python_job.id, ids)
        self.assertTrue(all(item["title"] == "Python Developer" for item in response.data))
        self.assertTrue(all(item["recommendation_mode"] == "SPARSE_PROFILE" for item in response.data))

    def test_strong_backend_profile_returns_high_confidence_backend_job(self):
        user = self.create_user(
            "backend_strong@example.com",
            competences=["Python", "Django", "PostgreSQL"],
            target_roles=["Backend Developer"],
            domaines_interet=["SAAS"],
            preferred_locations=["Tunis"],
            work_mode_preferences=["REMOTE"],
            remote_preference="REMOTE",
            employment_types=["FULL_TIME"],
            niveau_experience="JUNIOR",
            annees_experience=2,
            opportunity_types=["JOB"],
            onboarding_completed=True,
        )
        ProfileResume.objects.create(
            profile=user.profil,
            parsed_text="Backend Django APIs PostgreSQL Redis Celery",
            is_active=True,
        )
        user.profil.embedding_content_hash = build_profile_embedding_content_hash(user.profil)
        user.profil.embedding_features_hash = user.profil.embedding_content_hash
        user.profil.save(update_fields=["embedding_content_hash", "embedding_features_hash"])

        backend = self.create_opportunity(
            "Backend Developer Python Django",
            0.72,
            skills=["Python", "Django"],
            normalized_industries=["SAAS"],
            contract_type="CDI",
        )
        self.create_opportunity("General Office Assistant", 0.52, skills=["Excel"])

        response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], backend.id)
        self.assertEqual(response.data[0]["recommendation_confidence"], CONFIDENCE_HIGH)
        self.assertEqual(response.data[0]["profile_strength"], "HIGH")
        self.assertGreaterEqual(response.data[0]["evidence_summary"]["skill_overlap"], 2)
        self.assertTrue(response.data[0]["evidence_summary"]["role_match"])

    def test_role_only_profile_can_pass_with_title_role_overlap(self):
        user = self.create_user(
            "role_only@example.com",
            target_roles=["Backend Developer"],
            opportunity_types=["JOB"],
        )
        backend = self.create_opportunity("Backend Developer", 0.46)
        self.create_opportunity("HR Specialist", 0.50, skills=["Recruitment"])

        response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [backend.id])
        self.assertTrue(response.data[0]["evidence_summary"]["role_match"])

    def test_cv_only_profile_can_pass_on_resume_semantic_evidence(self):
        user = self.create_user("cv_only@example.com", opportunity_types=["JOB"])
        ProfileResume.objects.create(
            profile=user.profil,
            parsed_text="Backend Django APIs PostgreSQL Redis Celery",
            is_active=True,
        )
        user.profil.embedding_content_hash = build_profile_embedding_content_hash(user.profil)
        user.profil.embedding_features_hash = user.profil.embedding_content_hash
        user.profil.save(update_fields=["embedding_content_hash", "embedding_features_hash"])
        backend = self.create_opportunity("API Platform Engineer", 0.61)
        self.create_opportunity("Restaurant Manager", 0.45, skills=["Hospitality"])

        response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [backend.id])
        self.assertTrue(response.data[0]["evidence_summary"]["resume_signal"])

    def test_empty_profile_returns_limited_sparse_fallback(self):
        user = Utilisateur.objects.create_user(
            username="empty_profile@example.com",
            email="empty_profile@example.com",
            password="x",
        )
        user.profil.opportunity_types = ["JOB"]
        user.profil.save(update_fields=["opportunity_types"])
        for index in range(5):
            self.create_opportunity(f"Recent Job {index}", 0.20)

        response = self.get_recommendations(user, limit=10)

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data), 3)
        self.assertTrue(all(item["recommendation_confidence"] == "LOW" for item in response.data))
        self.assertTrue(all(item["recommendation_mode"] == "SPARSE_PROFILE" for item in response.data))

    def test_quality_gate_rejects_weak_location_or_experience_only_evidence(self):
        features = {"skills": ["Python"], "experience_level": "JUNIOR"}
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        opportunity = SimpleNamespace(
            titre="Adjoint Ressources Humaines",
            skills=["Excel"],
            semantic_score=0.44,
            match_score=0.44,
            experience_min=1,
            experience_max=2,
        )

        self.assertFalse(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
            )
        )

    def test_quality_gate_threshold_allows_exact_skill_match_for_sparse_profile(self):
        features = {"skills": ["Python"]}
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        opportunity = SimpleNamespace(
            titre="Python Developer",
            skills=["Python"],
            semantic_score=0.42,
            match_score=0.38,
        )

        self.assertTrue(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
            )
        )

    def test_confidence_requires_more_than_high_semantic_similarity(self):
        features = {"skills": ["Python"]}
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        opportunity = SimpleNamespace(
            titre="Generic Technology Role",
            skills=[],
            semantic_score=0.72,
            match_score=0.72,
        )
        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertEqual(
            compute_recommendation_confidence(
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            ),
            CONFIDENCE_MEDIUM,
        )

    def test_reasons_do_not_include_duplicates_or_single_word_skill_labels(self):
        user = self.create_user(
            "reason_quality@example.com",
            competences=["Python"],
            target_roles=["Python Backend Developer"],
            preferred_locations=["Tunis"],
            opportunity_types=["JOB"],
        )
        self.create_opportunity(
            "Python Backend Developer",
            0.65,
            skills=["Python"],
        )

        response = self.get_recommendations(user)

        reasons = response.data[0]["reasons"]
        self.assertEqual(len(reasons), len(set(reasons)))
        self.assertNotIn("Python", reasons)
        self.assertTrue(any("Python" in reason for reason in reasons))

    def test_multilingual_role_and_skill_evidence(self):
        features = {
            "skills": ["Python"],
            "target_roles": ["Développeur Backend"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        opportunity = SimpleNamespace(
            titre="Développeur Backend Python",
            skills=["Python"],
            semantic_score=0.53,
            match_score=0.53,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertEqual(evidence["skill_overlap"], 1)
        self.assertTrue(evidence["role_match"])

    def test_api_response_keeps_backward_compatibility_fields(self):
        user = self.create_user(
            "compat@example.com",
            competences=["Python"],
            opportunity_types=["JOB"],
        )
        self.create_opportunity("Python Developer", 0.50, skills=["Python"])

        response = self.get_recommendations(user)

        item = response.data[0]
        for field in ("score", "match_score", "semantic_score", "business_score", "reason", "reasons"):
            self.assertIn(field, item)
        for field in ("recommendation_confidence", "profile_strength", "recommendation_mode", "evidence_summary"):
            self.assertIn(field, item)

    def test_pgvector_retrieval_entrypoint_is_still_used(self):
        user = self.create_user(
            "pgvector_still_used@example.com",
            competences=["Python"],
            opportunity_types=["JOB"],
        )
        opportunity = self.create_opportunity("Python Developer", 0.50, skills=["Python"])

        with patch("ai.views.retrieve_recommendation_candidates", return_value=[opportunity]) as mocked:
            response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked.called)
        self.assertEqual(response.data[0]["id"], opportunity.id)
