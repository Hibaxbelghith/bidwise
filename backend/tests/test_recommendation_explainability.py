from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ai.embeddings import build_profile_embedding_content_hash, get_current_profile_embedding_model
from ai.explainability import build_recommendation_explanation
from ai.views import _serialize_recommendation
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import Utilisateur


class RecommendationExplainabilityTests(SimpleTestCase):
    def test_skills_match_reasons(self):
        opportunity = SimpleNamespace(
            titre="Backend Developer",
            skills=["Python", "Django", "Kubernetes"],
            semantic_score=0.8,
        )

        explanation = build_recommendation_explanation(
            {"skills": ["Python", "Django"]},
            opportunity,
        )

        self.assertIn("Strong Python + Django alignment", explanation["reasons"])

    def test_skills_gaps_are_constructive_and_limited(self):
        opportunity = SimpleNamespace(
            titre="Platform Engineer",
            skills=["Python", "Kubernetes", "Docker", "Terraform"],
            semantic_score=0.4,
        )

        explanation = build_recommendation_explanation(
            {"skills": ["Python"]},
            opportunity,
        )

        self.assertIn("Missing Kubernetes experience", explanation["gaps"])
        self.assertLessEqual(len(explanation["gaps"]), 3)

    def test_work_mode_reason(self):
        opportunity = SimpleNamespace(
            titre="Remote Backend Developer",
            availability="Remote",
            skills=[],
            semantic_score=0.0,
        )

        explanation = build_recommendation_explanation(
            {"work_modes": ["REMOTE"]},
            opportunity,
        )

        self.assertIn("Remote work preference aligned", explanation["reasons"])

    def test_industry_alignment_reason(self):
        opportunity = SimpleNamespace(
            titre="Backend Developer",
            skills=[],
            normalized_industries=["HEALTHCARE"],
            semantic_score=0.0,
        )

        explanation = build_recommendation_explanation(
            {"interests": ["HEALTHCARE"]},
            opportunity,
        )

        self.assertIn("Healthcare industry aligned", explanation["reasons"])

    def test_no_duplicate_reasons(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Remote Python Developer",
            skills=["Python"],
            availability="Remote",
            semantic_score=0.9,
            business_score=0.2,
            feedback_score=0.0,
            match_score=0.9,
            score_label="Top match",
            score_level="HIGH",
            reason=["Strong Python alignment", "Remote work preference aligned"],
            ville="Tunis",
            organisation_nom="Acme",
            type_opportunite="EMPLOI",
        )

        payload = _serialize_recommendation(
            opportunity,
            features={"skills": ["Python"], "work_modes": ["REMOTE"]},
        )

        self.assertEqual(len(payload["reasons"]), len(set(payload["reasons"])))

    def test_preference_reasons_are_suppressed_without_metier_evidence(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Digital Marketing Intern",
            skills=["Social Media"],
            availability="Remote",
            contract_type="Stage",
            ville="Tunis",
            semantic_score=0.35,
            business_score=0.2,
            feedback_score=0.0,
            match_score=0.30,
            reason=["Remote match", "Location match: Tunis"],
            organisation_nom="Acme",
            type_opportunite="STAGE",
        )

        payload = _serialize_recommendation(
            opportunity,
            features={
                "skills": ["React", "JavaScript"],
                "target_roles": ["Frontend Developer"],
                "work_modes": ["REMOTE"],
                "employment_types": ["INTERNSHIP"],
                "locations": ["Tunis"],
            },
        )

        self.assertNotIn("Remote work preference aligned", payload["reasons"])
        self.assertNotIn("Remote match", payload["reasons"])
        self.assertNotIn("Internship contract aligned", payload["reasons"])
        self.assertFalse(any(reason.startswith("Location aligned") for reason in payload["reasons"]))
        self.assertFalse(any(reason.startswith("Location match") for reason in payload["reasons"]))

    def test_strong_metier_explanations_are_preserved(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Remote Frontend Developer",
            skills=["React"],
            availability="Remote",
            contract_type="Stage",
            ville="Tunis",
            semantic_score=0.70,
            business_score=0.2,
            feedback_score=0.0,
            match_score=0.72,
            reason=[],
            organisation_nom="Acme",
            type_opportunite="STAGE",
        )

        payload = _serialize_recommendation(
            opportunity,
            features={
                "skills": ["React", "JavaScript"],
                "target_roles": ["Frontend Developer"],
                "work_modes": ["REMOTE"],
                "employment_types": ["INTERNSHIP"],
                "locations": ["Tunis"],
            },
        )

        self.assertIn("Strong React alignment", payload["reasons"])
        self.assertIn("Remote work preference aligned", payload["reasons"])

    def test_deterministic_ordering(self):
        opportunity = SimpleNamespace(
            titre="Remote Backend Developer",
            skills=["Python", "Django", "Kubernetes"],
            availability="Remote",
            normalized_industries=["HEALTHCARE"],
            ville="Tunis",
            semantic_score=0.9,
        )
        features = {
            "skills": ["Python", "Django"],
            "target_roles": ["Backend Developer"],
            "interests": ["HEALTHCARE"],
            "work_modes": ["REMOTE"],
            "locations": ["Tunis"],
        }

        self.assertEqual(
            build_recommendation_explanation(features, opportunity),
            build_recommendation_explanation(features.copy(), opportunity),
        )

    def test_multilingual_safe_output(self):
        opportunity = SimpleNamespace(
            titre="Développeur Python",
            skills=["Python", "Django"],
            normalized_industries=["SANTÉ"],
            semantic_score=0.8,
        )

        explanation = build_recommendation_explanation(
            {"skills": ["Python"], "interests": ["SANTÉ"], "resume_text": "مهندس Python"},
            opportunity,
        )

        self.assertIn("Strong Python alignment", explanation["reasons"])
        self.assertIn("Santé industry aligned", explanation["reasons"])

    def test_empty_noisy_profile_handling(self):
        opportunity = SimpleNamespace(
            titre="Software Engineer",
            skills=["API", "Python"],
            semantic_score=0.0,
        )

        explanation = build_recommendation_explanation({}, opportunity)

        self.assertNotIn("Missing API experience", explanation["gaps"])
        self.assertIn("Missing Python experience", explanation["gaps"])


class RecommendationExplainabilityApiTests(TestCase):
    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=384)
    def test_recommendation_api_exposes_reasons_and_gaps(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )
        user = Utilisateur.objects.create_user(
            username="explainability_user",
            email="explainability_user@example.com",
            password="x",
        )
        profile = user.profil
        profile.competences = ["Python", "Django"]
        profile.target_roles = ["Backend Developer"]
        profile.domaines_interet = ["HEALTHCARE"]
        profile.niveau_experience = "JUNIOR"
        profile.preferred_locations = ["Tunis"]
        profile.remote_preference = "REMOTE"
        profile.work_mode_preferences = ["REMOTE"]
        profile.employment_types = ["FULL_TIME"]
        profile.opportunity_types = ["JOB"]
        profile.embedding = [1.0] + [0.0] * 383
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = 384
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = build_profile_embedding_content_hash(profile)
        profile.embedding_features_hash = profile.embedding_content_hash
        profile.save()

        Opportunite.objects.create(
            titre="Remote Backend Developer",
            description="Python Django backend role",
            organisation_nom="Acme",
            ville="Tunis",
            availability="Remote",
            contract_type="Full time",
            skills=["Python", "Django", "Kubernetes"],
            normalized_industries=["HEALTHCARE"],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.now().date(),
            source=source,
            embedding_vector=[1.0] + [0.0] * 383,
            embedding_vector_pg=[1.0] + [0.0] * 383,
            embedding_model=get_current_profile_embedding_model(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/recommendations/?limit=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        payload = response.data[0]
        self.assertIn("reasons", payload)
        self.assertIn("reason", payload)
        self.assertIn("gaps", payload)
        self.assertIn("Strong Python + Django alignment", payload["reasons"])
        self.assertIn("Missing Kubernetes experience", payload["gaps"])
