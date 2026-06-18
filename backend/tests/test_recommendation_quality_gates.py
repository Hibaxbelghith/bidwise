from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from ai.embeddings import build_profile_embedding_content_hash, get_current_profile_embedding_model
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import (
    BUCKET_RELATED_REVIEW,
    BUCKET_STRONG_MATCH,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    build_recommendation_evidence,
    classify_recommendation_bucket,
    compute_recommendation_confidence,
    filter_ranked_recommendations,
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
        runtime_attrs = {}
        for key in ("match_score", "semantic_score", "recommendation_debug"):
            if key in overrides:
                runtime_attrs[key] = overrides.pop(key)
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
        opportunity = Opportunite.objects.create(**defaults)
        for key, value in runtime_attrs.items():
            setattr(opportunity, key, value)
        return opportunity

    def test_bucket_keeps_sparse_exact_junior_role_as_strong_match(self):
        opportunity = self.create_opportunity(
            "Junior Frontend developer",
            0.63,
            description="Junior Frontend developer",
            skills=[],
            match_score=0.68,
            semantic_score=0.63,
        )
        features = {
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
            "skills": ["React", "JavaScript"],
            "profile_skills": ["React", "JavaScript"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_STRONG_MATCH)
        self.assertIn("limited details", reason)

    def test_filter_orders_close_strong_matches_by_source_quality(self):
        linkedin = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://linkedin.example",
            type_source="SITE_EMPLOI",
        )
        keejob = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://keejob.example",
            type_source="SITE_EMPLOI",
        )
        linkedin_opportunity = self.create_opportunity(
            "Comptable LinkedIn",
            0.70,
            source=linkedin,
            skills=["Saisie comptable", "Excel"],
            match_score=0.73,
            semantic_score=0.70,
        )
        keejob_opportunity = self.create_opportunity(
            "Comptable Keejob",
            0.68,
            source=keejob,
            skills=["Saisie comptable", "Excel"],
            match_score=0.68,
            semantic_score=0.68,
        )
        features = {
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "skills": ["Saisie comptable", "Excel"],
            "profile_skills": ["Saisie comptable", "Excel"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
        }

        ordered = filter_ranked_recommendations(
            [linkedin_opportunity, keejob_opportunity],
            features=features,
            profile_strength={"level": "HIGH"},
            limit=2,
        )

        self.assertEqual([item.pk for item in ordered], [keejob_opportunity.pk, linkedin_opportunity.pk])
        self.assertGreater(linkedin_opportunity.match_score, keejob_opportunity.match_score)

    def test_bucket_moves_mid_senior_frontend_to_related_for_junior_profile(self):
        opportunity = self.create_opportunity(
            "Mid-Senior Frontend Engineer",
            0.64,
            skills=[],
            match_score=0.62,
            semantic_score=0.64,
        )
        opportunity.recommendation_debug = {"experience_gap_penalty": 0.03}
        features = {
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
            "skills": ["React", "JavaScript"],
            "profile_skills": ["React", "JavaScript"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("Seniority", reason)

    def test_bucket_moves_technician_role_to_review_for_engineer_profile(self):
        opportunity = self.create_opportunity(
            "Technicien Supérieur en Génie Civil - El Mourouj, Ben Arous",
            0.67,
            skills=["Dimensionnement"],
            match_score=0.70,
            semantic_score=0.67,
        )
        features = {
            "target_roles": ["Ingénieur génie civil travaux"],
            "roles": ["Ingénieur génie civil travaux"],
            "skills": ["Autocad", "MS Project"],
            "profile_skills": ["Autocad", "MS Project"],
            "experience_level": "JUNIOR",
            "education_level": "Bac+5",
            "locations": ["Ben Arous"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("qualification scope", reason)

    def test_bucket_moves_responsable_role_to_review_for_junior_profile(self):
        opportunity = self.create_opportunity(
            "Responsable Financier et Comptable - Tunis",
            0.62,
            skills=["Comptabilité", "Gestion", "Finance"],
            match_score=0.72,
            semantic_score=0.62,
        )
        features = {
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "skills": ["comptabilité", "gestion"],
            "profile_skills": ["comptabilité", "gestion"],
            "experience_level": "JUNIOR",
            "education_level": "Bac+3",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("LLM validation", reason)

    def test_bucket_keeps_exact_helpdesk_match_strong_when_llm_gap_is_only_ambiguous(self):
        opportunity = self.create_opportunity(
            "IT Helpdesk Officer",
            0.70,
            skills=["Support Helpdesk", "Windows", "Microsoft 365"],
            match_score=0.86,
            semantic_score=0.70,
            recommendation_debug={
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": True,
                    "seniority_gap": 1,
                    "qualification_gap": 0,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "reason": "Slight hierarchy gap; keep as reviewable",
                }
            },
        )
        features = {
            "target_roles": ["IT Helpdesk Officer"],
            "roles": ["IT Helpdesk Officer"],
            "skills": ["support helpdesk", "Windows", "Microsoft 365"],
            "profile_skills": ["support helpdesk", "Windows", "Microsoft 365"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_STRONG_MATCH)
        self.assertIn("Strong role", reason)

    def test_bucket_promotes_jobbert_title_match_without_structured_skills(self):
        opportunity = self.create_opportunity(
            "Procurement Specialist",
            0.59,
            skills=[],
            match_score=0.63,
            semantic_score=0.59,
        )
        features = {
            "target_roles": ["Procurement Specialist"],
            "roles": ["Procurement Specialist"],
            "skills": ["Vendor negotiation", "Supplier management"],
            "profile_skills": ["Vendor negotiation", "Supplier management"],
            "experience_level": "CONFIRME",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_STRONG_MATCH)
        self.assertIn("semantic title match", reason)

    def test_bucket_does_not_promote_semantic_title_match_with_family_mismatch(self):
        opportunity = self.create_opportunity(
            "DevOps Engineer",
            0.59,
            skills=[],
            match_score=0.63,
            semantic_score=0.59,
            extra_data={
                "llm_enrichment": {
                    "confidence": 1.0,
                    "family_confidence": 1.0,
                    "business_families": ["accounting_finance_audit"],
                }
            },
        )
        features = {
            "target_roles": ["DevOps Engineer"],
            "roles": ["DevOps Engineer"],
            "skills": ["Docker", "Kubernetes", "Terraform"],
            "profile_skills": ["Docker", "Kubernetes", "Terraform"],
            "profile_business_families": ["devops_cloud_infrastructure"],
            "profile_family_confidence": 1.0,
            "experience_level": "CONFIRME",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertTrue(evidence["llm_family_mismatch"])
        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("needs review", reason)

    def test_bucket_keeps_confirmed_accountant_in_review_despite_skill_evidence(self):
        opportunity = self.create_opportunity(
            "Comptable Confirmé - Tunis",
            0.64,
            skills=["Comptabilité", "Gestion"],
            match_score=0.82,
            semantic_score=0.64,
            recommendation_debug={
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": True,
                    "seniority_gap": 1,
                    "qualification_gap": 1,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "reason": "Slight hierarchy gap; keep as reviewable",
                }
            },
        )
        features = {
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "skills": ["comptabilité", "gestion"],
            "profile_skills": ["comptabilité", "gestion"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("hierarchy gap", reason.lower())

    def test_bucket_allows_compatible_confirmed_backend_when_role_and_semantic_are_strong(self):
        opportunity = self.create_opportunity(
            "Back End Developer",
            0.60,
            skills=["Docker"],
            match_score=0.86,
            semantic_score=0.60,
            recommendation_debug={
                "ai_metier_evidence": True,
                "role_semantic_score": 0.69,
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": True,
                    "seniority_gap": 1,
                    "qualification_gap": 0,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "is_compatible": True,
                    "reason": "Slight hierarchy gap; keep as reviewable",
                }
            },
        )
        features = {
            "target_roles": ["Backend Developer"],
            "roles": ["Backend Developer"],
            "skills": ["Python", "Django", "Docker"],
            "profile_skills": ["Python", "Django", "Docker"],
            "experience_level": "JUNIOR",
            "locations": ["Sousse"],
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_STRONG_MATCH)
        self.assertIn("Strong role", reason)

    def test_role_semantic_only_without_skills_needs_stronger_confirmation(self):
        opportunity = self.create_opportunity(
            "Platform Engineer",
            0.61,
            description=(
                "Build and maintain internal platform services with observability, deployment, "
                "and developer tooling responsibilities."
            ),
            skills=[],
            match_score=0.66,
            semantic_score=0.61,
            recommendation_debug={
                "ai_metier_evidence": True,
                "role_semantic_score": 0.70,
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": False,
                    "seniority_gap": 0,
                    "qualification_gap": 0,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "is_compatible": True,
                    "reason": "",
                },
            },
        )
        features = {
            "target_roles": ["Backend Developer"],
            "roles": ["Backend Developer"],
            "skills": ["Python", "Django", "Docker"],
            "profile_skills": ["Python", "Django", "Docker"],
            "experience_level": "JUNIOR",
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertIn("stronger semantic confirmation", reason)

    def test_skill_only_accounting_office_manager_stays_related_without_role_alignment(self):
        opportunity = self.create_opportunity(
            "Gestionnaire de Bureau (H/F) - Tunis",
            0.64,
            description=(
                "Gestion administrative et financiere, facturation clients et fournisseurs, "
                "suivi des reglements et documents comptables."
            ),
            skills=["Comptabilité", "Facturation", "Gestion administrative"],
            match_score=0.75,
            semantic_score=0.64,
            recommendation_debug={
                "ai_metier_evidence": True,
                "role_semantic_score": 0.41,
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": False,
                    "seniority_gap": 0,
                    "qualification_gap": 0,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "is_compatible": True,
                    "reason": "",
                },
            },
        )
        features = {
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "skills": ["Excel", "Audit", "Comptabilité", "Déclarations fiscales"],
            "profile_skills": ["Excel", "Audit", "Comptabilité", "Déclarations fiscales"],
            "experience_level": "JUNIOR",
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertFalse(evidence["role_match"])
        self.assertGreater(evidence["profile_skill_overlap"], 0)
        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertEqual(reason, "Relevant finance role, but accounting evidence needs review")

    def test_assistant_comptable_stays_strong_with_confirmed_role_alignment(self):
        opportunity = self.create_opportunity(
            "Assistant Comptable - Tunis",
            0.64,
            description="Saisie comptable, rapprochement bancaire, declarations fiscales et suivi administratif.",
            skills=["Comptabilité", "Excel", "Déclarations fiscales"],
            match_score=0.82,
            semantic_score=0.64,
            recommendation_debug={
                "ai_metier_evidence": True,
                "role_semantic_score": 0.69,
                "hierarchy_validation": {
                    "hierarchy_issue": "none",
                    "needs_llm": False,
                    "seniority_gap": 0,
                    "qualification_gap": 0,
                    "responsibility_gap": 0,
                    "score_multiplier": 1.0,
                    "is_compatible": True,
                    "reason": "",
                },
            },
        )
        features = {
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "skills": ["Excel", "Audit", "Comptabilité", "Déclarations fiscales"],
            "profile_skills": ["Excel", "Audit", "Comptabilité", "Déclarations fiscales"],
            "experience_level": "JUNIOR",
        }
        evidence = build_recommendation_evidence(features, opportunity)

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
            evidence=evidence,
        )

        self.assertTrue(evidence["role_match"])
        self.assertEqual(bucket, BUCKET_STRONG_MATCH)
        self.assertIn("Strong role", reason)

    def test_role_evidence_does_not_treat_customer_support_as_support_it(self):
        opportunity = self.create_opportunity(
            "Customer Service Support",
            0.40,
            skills=[],
        )
        opportunity.match_score = 0.35
        opportunity.semantic_score = 0.40
        features = {
            "target_roles": ["Support IT"],
            "roles": ["Support IT"],
            "skills": ["Windows"],
        }

        evidence = build_recommendation_evidence(features, opportunity)

        self.assertFalse(evidence["role_match"])
        self.assertEqual(evidence["matched_roles"], [])

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
            extracted_skills=["Django", "PostgreSQL", "Redis", "Celery"],
            semantic_resume_status="SUCCEEDED",
            semantic_resume_confidence=0.9,
            semantic_resume_metadata={
                "business_families": ["software_web"],
                "family_confidence": 0.9,
                "target_roles": ["Backend Developer"],
                "canonical_role": "Backend Developer",
            },
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

    def test_strict_internship_profile_gets_labeled_contract_alternative_with_metier_evidence(self):
        user = self.create_user(
            "frontend_internship_fallback@example.com",
            competences=["React", "JavaScript", "HTML", "CSS"],
            target_roles=["Frontend Developer"],
            preferred_locations=["Tunis"],
            work_mode_preferences=["REMOTE"],
            remote_preference="REMOTE",
            employment_types=["INTERNSHIP"],
            opportunity_types=["INTERNSHIP"],
            niveau_experience="DEBUTANT",
            onboarding_completed=True,
        )
        frontend = self.create_opportunity(
            "Junior Frontend Developer",
            0.72,
            skills=["React", "JavaScript"],
            availability="Remote",
            contract_type="CDI",
            type_opportunite=TypeOpportunite.EMPLOI,
        )
        self.create_opportunity(
            "Digital Marketing Intern",
            0.45,
            skills=["Social Media"],
            availability="Remote",
            contract_type="Stage",
            type_opportunite=TypeOpportunite.STAGE,
        )

        response = self.get_recommendations(user, limit=5)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [frontend.id])
        self.assertEqual(response.data[0]["score_label"], "Alternative match")
        self.assertEqual(response.data[0]["recommendation_mode"], "CONTRACT_ALTERNATIVE")
        self.assertIn("Outside preferred contract type", response.data[0]["reasons"])
        self.assertGreaterEqual(response.data[0]["evidence_summary"]["skill_overlap"], 1)

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
        backend = self.create_opportunity("Backend Developer", 0.75)
        self.create_opportunity("Restaurant Manager", 0.45, skills=["Hospitality"])

        response = self.get_recommendations(user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [backend.id])
        self.assertTrue(response.data[0]["evidence_summary"]["resume_signal"])

    def test_empty_profile_does_not_return_recent_fallback_by_default(self):
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
        self.assertEqual(response.data, [])

    @override_settings(RECOMMENDATION_SHOW_RECENT_FALLBACK=True)
    def test_recent_fallback_is_feature_flagged_and_limited(self):
        user = Utilisateur.objects.create_user(
            username="empty_profile_fallback@example.com",
            email="empty_profile_fallback@example.com",
            password="x",
        )
        user.profil.opportunity_types = ["JOB"]
        user.profil.save(update_fields=["opportunity_types"])
        for index in range(5):
            self.create_opportunity(f"Recent Fallback Job {index}", 0.20)

        response = self.get_recommendations(user, limit=10)

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data), 3)
        self.assertTrue(all(item["score"] == 0.0 for item in response.data))
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

    def test_accounting_profile_keeps_management_control_role_in_related(self):
        features = {
            "profile_skills": ["Comptabilite generale", "Saisie comptable", "Excel"],
            "skills": ["Comptabilite generale", "Saisie comptable", "Excel"],
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "experience_level": "JUNIOR",
            "experience_years": 2,
        }
        opportunity = SimpleNamespace(
            titre="Assistant controle de gestion",
            skills=[
                "Controle de gestion",
                "Analyse de performance",
                "Reporting financier",
                "Excel",
            ],
            semantic_score=0.63,
            match_score=0.63,
            experience_min=2,
            experience_max=5,
            recommendation_debug={"opportunity_quality_score": 0.90},
        )

        bucket, reason = classify_recommendation_bucket(
            features=features,
            opportunity=opportunity,
        )

        self.assertEqual(bucket, BUCKET_RELATED_REVIEW)
        self.assertEqual(reason, "Relevant finance role, but accounting evidence needs review")

    def test_explicit_backend_profile_rejects_resume_only_hr_false_positive(self):
        features = {
            "profile_skills": ["Python", "Django", "FastAPI"],
            "skills": ["Python", "Django", "FastAPI", "human resources"],
            "target_roles": ["Python Backend Developer"],
            "roles": ["Python Backend Developer"],
            "resume_text": "Older resume mentions human resources.",
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Human Resources Manager",
            skills=[],
            normalized_industries=[],
            semantic_score=0.63,
            match_score=0.63,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertTrue(evidence["resume_signal"])
        self.assertEqual(evidence["profile_skill_overlap"], 0)
        self.assertFalse(evidence["role_match"])
        self.assertFalse(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            )
        )

    def test_cv_only_profile_can_still_pass_resume_signal(self):
        features = {
            "skills": ["human resources"],
            "resume_text": "Human resources manager resume.",
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        opportunity = SimpleNamespace(
            titre="Human Resources Manager",
            skills=[],
            normalized_industries=[],
            semantic_score=0.63,
            match_score=0.63,
        )

        self.assertTrue(
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

    def test_role_aligned_backend_title_outranks_generic_fullstack_when_scores_are_close(self):
        features = {
            "skills": ["Python", "Django", "FastAPI"],
            "target_roles": ["Python Backend Developer"],
            "roles": ["Python Backend Developer"],
            "locations": ["Tunis"],
            "work_modes": ["HYBRID"],
        }
        backend = SimpleNamespace(
            id=1,
            titre="Python Backend Developer",
            description="Build Django and FastAPI APIs.",
            skills=["Python", "Django", "FastAPI", "PostgreSQL"],
            ville="Tunis",
            availability="Hybrid",
            embedding_vector=vector_with_similarity(0.64),
            date_publication=date.today(),
        )
        fullstack = SimpleNamespace(
            id=2,
            titre="Full Stack Developer",
            description="Work across Python Django APIs and React frontends.",
            skills=["Python", "Django", "React", "JavaScript"],
            ville="Tunis",
            availability="Hybrid",
            embedding_vector=vector_with_similarity(0.66),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(
            user_vector(),
            [fullstack, backend],
            features=features,
            mode="complete",
        )

        self.assertEqual(ranked[0].titre, "Python Backend Developer")

    def test_role_plus_skills_outranks_role_only_frontend_match(self):
        features = {
            "profile_skills": ["React", "JavaScript", "Node.js"],
            "skills": ["React", "JavaScript", "Node.js"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
            "locations": ["Tunis"],
            "work_modes": ["REMOTE"],
        }
        role_only = SimpleNamespace(
            id=1,
            titre="Junior Frontend Developer",
            description="Role: Junior Frontend developer.",
            skills=[],
            ville="Tunis",
            availability="On-site",
            semantic_score=0.67,
            embedding_vector=vector_with_similarity(0.67),
            date_publication=date.today(),
        )
        react_frontend = SimpleNamespace(
            id=2,
            titre="Frontend React Developer",
            description="Create React and TypeScript user interfaces.",
            skills=["React", "TypeScript", "JavaScript", "CSS"],
            ville="Tunis",
            availability="Remote",
            semantic_score=0.65,
            embedding_vector=vector_with_similarity(0.65),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(
            user_vector(),
            [role_only, react_frontend],
            features=features,
            mode="complete",
        )

        self.assertEqual(ranked[0].titre, "Frontend React Developer")

    def test_frontend_role_and_skills_outrank_backend_heavy_javascript_match(self):
        features = {
            "profile_skills": ["React", "JavaScript", "Node.js"],
            "skills": ["React", "JavaScript", "Node.js"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
            "locations": ["Tunis"],
            "work_modes": ["REMOTE"],
        }
        backend_heavy_fullstack = SimpleNamespace(
            id=1,
            titre="DÃ©veloppeur Fullstack JavaScript Senior - Tunis",
            description="Backend prioritaire Node.js NestJS Express APIs. Frontend React appreciated.",
            skills=["DÃ©veloppeur Backend Senior JS", "Node.js Expert", "NestJS", "Express.js", "JAVASCRIPT", "NODE JS", "REACT"],
            ville="Tunis",
            availability="Hybrid",
            embedding_vector=vector_with_similarity(0.68),
            date_publication=date.today(),
        )
        frontend_react = SimpleNamespace(
            id=2,
            titre="Frontend React Developer",
            description="Create React and TypeScript user interfaces.",
            skills=["React", "TypeScript", "JavaScript", "CSS"],
            ville="Tunis",
            availability="Remote",
            embedding_vector=vector_with_similarity(0.66),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(
            user_vector(),
            [backend_heavy_fullstack, frontend_react],
            features=features,
            mode="complete",
        )

        self.assertEqual(ranked[0].titre, "Frontend React Developer")
        self.assertGreater(
            ranked[0].recommendation_debug["business_components"]["role_bonus"],
            0,
        )

    def test_confidence_is_medium_for_role_only_match_without_skills(self):
        features = {
            "profile_skills": ["React", "JavaScript"],
            "skills": ["React", "JavaScript"],
            "profile_business_families": ["software_web"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Junior Frontend Developer",
            skills=[],
            normalized_industries=[],
            semantic_score=0.72,
            match_score=0.72,
        )
        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertEqual(evidence["metier_signal_count"], 1)
        self.assertEqual(
            compute_recommendation_confidence(
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            ),
            CONFIDENCE_MEDIUM,
        )

    def test_isolated_excel_match_has_lower_score_than_comptable_role(self):
        features = {
            "profile_skills": ["ComptabilitÃ©", "Excel", "Sage"],
            "skills": ["ComptabilitÃ©", "Excel", "Sage"],
            "target_roles": ["Comptable"],
            "roles": ["Comptable"],
            "locations": ["Tunis"],
        }
        comptable = SimpleNamespace(
            id=1,
            titre="Comptable Saisie",
            description="Role: Comptable saisie.",
            skills=[],
            ville="Tunis",
            embedding_vector=vector_with_similarity(0.63),
            date_publication=date.today(),
        )
        excel_only = SimpleNamespace(
            id=2,
            titre="Specialist Operational Excellence Methods Tools",
            description="Operational excellence methods and tools.",
            skills=["Excel"],
            ville="Tunis",
            embedding_vector=vector_with_similarity(0.63),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(user_vector(), [excel_only, comptable], features=features)

        self.assertEqual(ranked[0].titre, "Comptable Saisie")

    def test_llm_business_family_boosts_matching_family(self):
        features = {
            "profile_skills": ["React", "JavaScript"],
            "skills": ["React", "JavaScript"],
            "profile_business_families": ["software_web"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
        }
        frontend = SimpleNamespace(
            id=1,
            titre="UI Developer",
            description="Build user interfaces.",
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.9,
                    "family_confidence": 0.9,
                    "business_families": ["frontend"],
                }
            },
            embedding_vector=vector_with_similarity(0.63),
            date_publication=date.today(),
        )
        sales = SimpleNamespace(
            id=2,
            titre="Business Development Manager",
            description="Sales pipeline and client portfolio.",
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.9,
                    "family_confidence": 0.9,
                    "business_families": ["sales"],
                }
            },
            embedding_vector=vector_with_similarity(0.58),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(user_vector(), [sales, frontend], features=features)

        self.assertEqual(ranked[0].titre, "UI Developer")
        self.assertIn("Related job family signal detected", ranked[0].reason)
        self.assertGreater(
            ranked[0].recommendation_debug["business_components"]["llm_business_family_bonus"],
            0,
        )
        self.assertGreater(
            ranked[1].recommendation_debug["llm_business_family_mismatch_penalty"],
            0,
        )

    def test_low_score_family_only_match_does_not_show_job_family_reason(self):
        features = {
            "profile_skills": ["Windows", "Active Directory"],
            "skills": ["Windows", "Active Directory"],
            "profile_business_families": ["it_network_support"],
            "profile_family_confidence": 0.9,
            "target_roles": ["Technicien support informatique"],
            "roles": ["Technicien support informatique"],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Agent de Service Support Agent d Entretien",
            description="Entretien des locaux et services generaux.",
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.9,
                    "family_confidence": 0.9,
                    "business_families": ["it_network_support"],
                }
            },
            embedding_vector=vector_with_similarity(0.44),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(user_vector(), [opportunity], features=features)

        self.assertNotIn("Related job family signal detected", ranked[0].reason)

    def test_clear_devops_profile_strictly_penalizes_accounting_family(self):
        features = {
            "profile_skills": ["Docker", "Kubernetes", "Terraform"],
            "skills": ["Docker", "Kubernetes", "Terraform"],
            "profile_business_families": ["devops", "it_network_support"],
            "profile_family_confidence": 1.0,
            "target_roles": ["DevOps Engineer"],
            "roles": ["DevOps Engineer"],
        }
        incompatible = SimpleNamespace(
            id=1,
            titre="DevOps Accountant ERP Specialist",
            description="Maintain ERP automation tooling while handling accounting operations.",
            skills=["Docker", "Terraform"],
            extra_data={
                "llm_enrichment": {
                    "confidence": 1.0,
                    "family_confidence": 1.0,
                    "business_families": ["accounting_finance_audit"],
                }
            },
            embedding_vector=vector_with_similarity(0.62),
            date_publication=date.today(),
        )
        compatible = SimpleNamespace(
            id=2,
            titre="DevOps Accountant ERP Specialist",
            description=incompatible.description,
            skills=list(incompatible.skills),
            extra_data={
                "llm_enrichment": {
                    "confidence": 1.0,
                    "family_confidence": 1.0,
                    "business_families": ["it_network_support"],
                }
            },
            embedding_vector=vector_with_similarity(0.62),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        incompatible_ranked = rank_opportunities(
            user_vector(),
            [incompatible],
            features=features,
        )[0]
        compatible_ranked = rank_opportunities(
            user_vector(),
            [compatible],
            features=features,
        )[0]

        self.assertAlmostEqual(
            incompatible_ranked.recommendation_debug["llm_business_family_mismatch_penalty"],
            0.15,
        )
        self.assertEqual(
            compatible_ranked.recommendation_debug["llm_business_family_mismatch_penalty"],
            0.0,
        )
        self.assertGreaterEqual(
            compatible_ranked.match_score - incompatible_ranked.match_score,
            0.15,
        )

    def test_llm_family_match_counts_as_metier_evidence(self):
        features = {
            "profile_skills": ["Accounting", "Excel"],
            "skills": ["Accounting", "Excel"],
            "profile_business_families": ["accounting_finance"],
            "profile_family_confidence": 0.9,
            "target_roles": ["Accountant"],
            "roles": ["Accountant"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Finance Operations Analyst",
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.88,
                    "family_confidence": 0.9,
                    "business_families": ["accounting_finance"],
                }
            },
            semantic_score=0.45,
            match_score=0.45,
        )

    def test_llm_profile_family_match_counts_for_it_support_without_skill_keywords(self):
        features = {
            "profile_skills": ["Windows"],
            "skills": ["Windows"],
            "profile_business_families": ["it_network_support"],
            "profile_family_confidence": 0.91,
            "target_roles": ["Technicien support informatique"],
            "roles": ["Technicien support informatique"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Technicien Support & Maintenance",
            skills=["Windows"],
            extra_data={
                "llm_enrichment": {
                    "confidence": 0.9,
                    "family_confidence": 0.9,
                    "business_families": ["it_network_support"],
                }
            },
            semantic_score=0.44,
            match_score=0.44,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertTrue(evidence["llm_family_match"])
        self.assertFalse(evidence["llm_family_mismatch"])

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertTrue(evidence["llm_family_match"])
        self.assertTrue(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            )
        )

    def test_network_support_profile_does_not_match_hr_support_title(self):
        features = {
            "profile_skills": ["Cisco", "BGP", "Routing", "Support"],
            "skills": ["Cisco", "BGP", "Routing", "Support"],
            "target_roles": ["Network Engineer"],
            "roles": ["Network Engineer"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        hr_support = SimpleNamespace(
            titre="Junior HR Support Specialist",
            description="Human resources support, onboarding and HR administration.",
            skills=[],
            semantic_score=0.45,
            match_score=0.45,
        )
        tech_support = SimpleNamespace(
            titre="Technical Support Specialist",
            description="Technical IT support for networks, servers and routing incidents.",
            skills=["Support"],
            semantic_score=0.45,
            match_score=0.45,
        )

        hr_evidence = build_recommendation_evidence(features, hr_support, profile_strength)
        tech_evidence = build_recommendation_evidence(features, tech_support, profile_strength)

        self.assertEqual(hr_evidence["skill_overlap"], 0)
        self.assertEqual(tech_evidence["skill_overlap"], 1)

    def test_network_support_profile_does_not_match_service_cleaning_support(self):
        features = {
            "profile_skills": ["Cisco", "BGP", "Routing", "Support"],
            "skills": ["Cisco", "BGP", "Routing", "Support"],
            "target_roles": ["Network Engineer"],
            "roles": ["Network Engineer"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Agent de Service Support d'Entretien",
            description=(
                "Principales taches et responsabilites: entretien des locaux, "
                "nettoyage des sols et depoussierage des surfaces."
            ),
            skills=[],
            semantic_score=0.42,
            match_score=0.42,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertEqual(evidence["skill_overlap"], 0)

    def test_frontend_profile_accepts_title_family_without_structured_skills(self):
        features = {
            "profile_skills": ["React", "JavaScript", "Node.js"],
            "skills": ["React", "JavaScript", "Node.js"],
            "profile_business_families": ["software_web"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Mid-Senior Frontend Engineer - Design System",
            description="Build component libraries and user interfaces.",
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "business_families": ["software_web"],
                    "family_confidence": 0.9,
                    "confidence": 0.9,
                }
            },
            semantic_score=0.63,
            match_score=0.67,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertTrue(evidence["llm_family_match"])
        self.assertTrue(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            )
        )

    def test_frontend_profile_rejects_incompatible_title_family_despite_description_noise(self):
        features = {
            "profile_skills": ["React", "JavaScript", "Node.js"],
            "skills": ["React", "JavaScript", "Node.js"],
            "profile_business_families": ["software_web"],
            "target_roles": ["Frontend Developer"],
            "roles": ["Frontend Developer"],
        }
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=True), features)
        opportunity = SimpleNamespace(
            titre="Multilingual Talent Acquisition Specialist",
            description=(
                "Recruitment role with dashboard reporting, candidate data, "
                "marketing coordination, support, and design collaboration."
            ),
            skills=[],
            extra_data={
                "llm_enrichment": {
                    "business_families": ["hr_administration"],
                    "family_confidence": 0.9,
                    "confidence": 0.9,
                }
            },
            semantic_score=0.63,
            match_score=0.61,
        )

        evidence = build_recommendation_evidence(features, opportunity, profile_strength)

        self.assertTrue(evidence["llm_family_mismatch"])
        self.assertFalse(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=opportunity,
                profile_strength=profile_strength,
                evidence=evidence,
            )
        )

    def test_sector_alignment_is_a_lightweight_ranking_signal(self):
        features = {
            "profile_skills": ["Python", "Django"],
            "skills": ["Python", "Django"],
            "target_roles": ["Backend Developer"],
            "roles": ["Backend Developer"],
            "interests": ["Finance"],
            "locations": ["Tunis"],
        }
        finance_backend = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            description="Python Django APIs for insurance and banking products.",
            skills=["Python", "Django"],
            normalized_industries=["FINTECH"],
            extra_data={"company_sector": "Assurance, Banque"},
            ville="Tunis",
            embedding_vector=vector_with_similarity(0.63),
            date_publication=date.today(),
        )
        generic_backend = SimpleNamespace(
            id=2,
            titre="Internal Tools Backend Developer",
            description="Python Django APIs for internal business tools.",
            skills=["Python", "Django"],
            normalized_industries=[],
            extra_data={},
            ville="Tunis",
            embedding_vector=vector_with_similarity(0.50),
            date_publication=date.today(),
        )

        from ai.recommendation_service import rank_opportunities

        ranked = rank_opportunities(
            user_vector(),
            [generic_backend, finance_backend],
            features=features,
            mode="complete",
        )

        self.assertEqual(ranked[0].id, finance_backend.id)
        self.assertGreater(
            ranked[0].recommendation_debug["business_components"]["sector_bonus"],
            0,
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
        opportunity = self.create_opportunity(
            "Python Developer",
            0.50,
            description="Build Python services and APIs.",
            source_item_url="https://example.test/jobs/python-developer",
            skills=["Python"],
        )

        response = self.get_recommendations(user)

        item = response.data[0]
        for field in ("score", "match_score", "semantic_score", "business_score", "reason", "reasons"):
            self.assertIn(field, item)
        for field in ("recommendation_confidence", "profile_strength", "recommendation_mode", "evidence_summary"):
            self.assertIn(field, item)
        self.assertEqual(item["description"], opportunity.description)
        self.assertEqual(item["source_item_url"], opportunity.source_item_url)
        self.assertEqual(item["skills"], ["Python"])
        self.assertEqual(item["source"]["nom"], self.source.nom)

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
