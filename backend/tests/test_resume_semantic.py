from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from ai.embeddings import build_user_embedding_text
from ai.profile_strength import compute_profile_strength
from ai.quality_gates import passes_recommendation_quality_gate
from ai.recommendation_service import rank_opportunities
from ai.user_features import build_user_features
from users.models import ProfileResume, Utilisateur
from users.resume_semantic.candidate_quality import filter_resume_skill_candidates
from users.resume_semantic.esco_mapping import map_to_esco
from users.resume_semantic.extraction import extract_skill_candidates
from users.resume_semantic.models import (
    SEMANTIC_RESUME_VERSION,
    SEMANTIC_STATUS_SKIPPED,
    SEMANTIC_STATUS_SUCCEEDED,
    SkillCandidate,
)
from users.resume_semantic.normalization import detect_languages, normalize_skill_label
from users.resume_semantic.service import enrich_resume_text, process_profile_resume_semantics


class ResumeSemanticExtractionTests(SimpleTestCase):
    def test_exact_tech_extraction_and_mapping(self):
        signals = enrich_resume_text(
            "Python backend engineer with Django REST, Postgres, Redis and Celery.",
            use_model=False,
            allow_semantic_mapping=False,
        )

        self.assertIn("python", signals.skills)
        self.assertIn("django", signals.tools)
        self.assertIn("postgresql", signals.tools)
        self.assertIn("redis", signals.tools)
        self.assertIn("celery", signals.tools)
        self.assertGreater(signals.semantic_confidence, 0.0)

    def test_synonym_normalization_examples(self):
        self.assertEqual(normalize_skill_label("Django REST"), "django")
        self.assertEqual(normalize_skill_label("K8s"), "kubernetes")
        self.assertEqual(normalize_skill_label("Postgres"), "postgresql")
        self.assertEqual(normalize_skill_label("PyTorch"), "machine learning")
        self.assertEqual(normalize_skill_label("CI/CD pipelines"), "devops")

    def test_multilingual_extraction_preserves_unicode(self):
        text = (
            "Développeur backend Python Django API REST. "
            "مهندس برمجيات بايثون لديه خبرة في واجهات API و PostgreSQL."
        )

        signals = enrich_resume_text(text, use_model=False, allow_semantic_mapping=False)

        self.assertIn("fr", signals.languages_detected)
        self.assertIn("ar", signals.languages_detected)
        self.assertIn("python", signals.skills)
        self.assertIn("django", signals.tools)
        self.assertIn("postgresql", signals.tools)

    def test_duplicate_removal_and_noisy_cv_handling(self):
        candidates = extract_skill_candidates(
            "Python Python python mission profile backend Django Django REST APIs",
            use_model=False,
        )
        labels = [candidate.text.casefold() for candidate in candidates]

        self.assertEqual(len(labels), len(set(labels)))
        self.assertNotIn("mission", labels)

    def test_semantic_mapping_thresholding_without_alias_match(self):
        self.assertEqual(map_to_esco(["unknown internal tool"], allow_semantic=False), [])

    def test_semantic_mapping_can_use_cosine_when_enabled(self):
        fake_vectors = tuple(
            tuple([1.0, 0.0]) if index == 0 else tuple([0.0, 1.0])
            for index in range(31)
        )
        with patch("users.resume_semantic.esco_mapping._encode_with_model", return_value=[[1.0, 0.0]]):
            with patch("users.resume_semantic.esco_mapping._canonical_embeddings", return_value=fake_vectors):
                mapped = map_to_esco(["server side scripting"], threshold=0.80, allow_semantic=True)

        self.assertEqual(mapped[0]["canonical"], "python")
        self.assertEqual(mapped[0]["model"], "BAAI/bge-m3")

    def test_language_detection_handles_english_french_arabic(self):
        languages = detect_languages("Python engineer. Développeur backend. مهندس بايثون.")

        self.assertEqual(languages, ["ar", "fr", "en"])

    def test_candidate_quality_filter_rejects_phrase_fragments_but_keeps_real_skills(self):
        accepted, rejected = filter_resume_skill_candidates(
            [
                SkillCandidate(text="React", source="lexical", confidence=0.9),
                SkillCandidate(
                    text="et développer un portefeuille de clients",
                    source="escoxlmr",
                    confidence=0.8,
                ),
                SkillCandidate(text="opportunités", source="escoxlmr", confidence=0.7),
                SkillCandidate(text="d", source="escoxlmr", confidence=0.6),
            ]
        )

        self.assertEqual([candidate.text for candidate in accepted], ["React"])
        self.assertEqual(
            [candidate.reason for candidate in rejected],
            ["phrase_fragment", "generic_business_term", "too_short"],
        )

    def test_candidate_quality_keeps_market_skills_and_rejects_generic_cv_noise(self):
        accepted, rejected = filter_resume_skill_candidates(
            [
                SkillCandidate(text="Python", source="lexical", confidence=0.95),
                SkillCandidate(text="Django", source="lexical", confidence=0.95),
                SkillCandidate(text="React", source="lexical", confidence=0.95),
                SkillCandidate(text="Excel", source="lexical", confidence=0.95),
                SkillCandidate(text="Sage", source="lexical", confidence=0.95),
                SkillCandidate(text="etre", source="model", confidence=0.8),
                SkillCandidate(text="proposer", source="model", confidence=0.8),
                SkillCandidate(text="equipe", source="model", confidence=0.8),
                SkillCandidate(text="être", source="model", confidence=0.8),
                SkillCandidate(text="à la pression", source="model", confidence=0.8),
                SkillCandidate(text="équipe", source="model", confidence=0.8),
                SkillCandidate(text="Assurer", source="model", confidence=0.8),
                SkillCandidate(text="Maintenir", source="model", confidence=0.8),
                SkillCandidate(text="Prospec", source="model", confidence=0.8),
                SkillCandidate(text="creating", source="model", confidence=0.8),
                SkillCandidate(text="robust and scalable systems", source="model", confidence=0.8),
                SkillCandidate(text="reusable components", source="model", confidence=0.8),
                SkillCandidate(text="force", source="model", confidence=0.8),
                SkillCandidate(text="pression", source="model", confidence=0.8),
            ]
        )

        self.assertEqual(
            [candidate.text for candidate in accepted],
            ["Python", "Django", "React", "Excel", "Sage"],
        )
        self.assertEqual(
            {candidate.text: candidate.reason for candidate in rejected},
            {
                "etre": "generic_action_term",
                "proposer": "generic_action_term",
                "equipe": "generic_business_term",
                "être": "generic_noise_term",
                "à la pression": "generic_noise_term",
                "équipe": "generic_noise_term",
                "Assurer": "generic_action_term",
                "Maintenir": "generic_action_term",
                "Prospec": "generic_action_term",
                "creating": "generic_action_term",
                "robust and scalable systems": "non_skill_phrase",
                "reusable components": "non_skill_phrase",
                "force": "generic_business_term",
                "pression": "generic_business_term",
            },
        )


class FakeResumeQuerySet:
    def __init__(self, resumes):
        self.resumes = resumes

    def only(self, *fields):
        return self

    def first(self):
        return self.resumes[0] if self.resumes else None


class FakeResumeManager:
    def __init__(self, resumes):
        self.resumes = resumes

    def filter(self, **kwargs):
        filtered = self.resumes
        for key, expected in kwargs.items():
            filtered = [resume for resume in filtered if getattr(resume, key, None) == expected]
        return FakeResumeQuerySet(filtered)


def semantic_profile(*, skills=None, domains=None, tools=None, languages=None):
    return SimpleNamespace(
        competences=[],
        domaines_interet=[],
        target_roles=[],
        niveau_experience="",
        annees_experience=None,
        preferred_locations=[],
        remote_preference="",
        work_mode_preferences=[],
        employment_types=[],
        compensation_expectation=None,
        onboarding_completed=False,
        resumes=FakeResumeManager(
            [
                SimpleNamespace(
                    is_active=True,
                    parsed_text="raw fallback text",
                    extracted_skills=skills or [],
                    extracted_domains=domains or [],
                    extracted_tools=tools or [],
                    extracted_languages=languages or ["en"],
                    semantic_resume_confidence=0.86,
                    semantic_resume_status="SUCCEEDED",
                )
            ]
        ),
    )


def opportunity(title, *, skills, vector=None):
    return SimpleNamespace(
        id=abs(hash(title)) % 10000,
        titre=title,
        skills=skills,
        embedding_vector=vector or [1.0, 0.0],
        date_publication=None,
        organisation_nom="Benchmark",
    )


class ResumeSemanticRecommendationImpactTests(SimpleTestCase):
    def test_backend_cv_improves_backend_job_score(self):
        baseline = build_user_features(SimpleNamespace())
        enriched = build_user_features(
            semantic_profile(skills=["python"], domains=["backend"], tools=["django", "postgresql"])
        )
        baseline_ranked = rank_opportunities(
            [1.0, 0.0],
            [opportunity("Python Backend Developer", skills=["python", "django", "postgresql"])],
            features=baseline,
            mode="partial",
        )
        baseline_score = baseline_ranked[0].business_score
        enriched_ranked = rank_opportunities(
            [1.0, 0.0],
            [opportunity("Python Backend Developer", skills=["python", "django", "postgresql"])],
            features=enriched,
            mode="partial",
        )

        self.assertGreater(enriched_ranked[0].business_score, baseline_score)

    def test_devops_cv_improves_devops_job_quality_gate(self):
        features = build_user_features(
            semantic_profile(domains=["devops"], tools=["docker", "kubernetes"])
        )
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        devops_job = opportunity("DevOps Engineer", skills=["docker", "kubernetes"])
        ranked = rank_opportunities([1.0, 0.0], [devops_job], features=features, mode="partial")

        self.assertTrue(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=ranked[0],
                profile_strength=profile_strength,
            )
        )

    def test_hr_cv_does_not_improve_ai_job(self):
        features = build_user_features(
            semantic_profile(domains=["human resources"], tools=[], skills=["recruitment"])
        )
        profile_strength = compute_profile_strength(SimpleNamespace(onboarding_completed=False), features)
        ai_job = opportunity("AI Engineer", skills=["machine learning", "python"], vector=[0.2, 0.98])
        ranked = rank_opportunities([1.0, 0.0], [ai_job], features=features, mode="partial")

        self.assertFalse(
            passes_recommendation_quality_gate(
                features=features,
                opportunity=ranked[0],
                profile_strength=profile_strength,
            )
        )

    def test_sparse_profile_gets_cv_uplift(self):
        sparse_profile = SimpleNamespace(
            competences=["python"],
            domaines_interet=[],
            target_roles=[],
            niveau_experience="",
            annees_experience=None,
            preferred_locations=[],
            remote_preference="",
            work_mode_preferences=[],
            employment_types=[],
            compensation_expectation=None,
            onboarding_completed=False,
        )
        sparse_features = build_user_features(sparse_profile)
        cv_features = build_user_features(
            semantic_profile(skills=["python"], domains=["backend"], tools=["django"])
        )
        sparse_ranked = rank_opportunities(
            [1.0, 0.0],
            [opportunity("Django Engineer", skills=["python", "django"])],
            features=sparse_features,
            mode="partial",
        )
        sparse_score = sparse_ranked[0].business_score
        cv_ranked = rank_opportunities(
            [1.0, 0.0],
            [opportunity("Django Engineer", skills=["python", "django"])],
            features=cv_features,
            mode="partial",
        )

        self.assertGreater(cv_ranked[0].business_score, sparse_score)

    def test_multilingual_cv_uplift(self):
        features = build_user_features(
            semantic_profile(
                skills=["python"],
                domains=["backend"],
                tools=["django", "postgresql"],
                languages=["ar", "fr", "en"],
            )
        )
        backend_ar = opportunity("مهندس برمجيات بايثون", skills=["python", "django"])
        ranked = rank_opportunities([1.0, 0.0], [backend_ar], features=features, mode="partial")

        self.assertGreater(ranked[0].business_score, 0.0)
        self.assertIn("ar", features["semantic_resume_languages"])


@override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2, LLM_ENRICHMENT_ENABLED=False)
class ResumeSemanticServiceTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="semantic_resume_user",
            email="semantic_resume_user@example.com",
            password="x",
        )
        self.profile = self.user.profil

    def create_resume(self, text):
        return ProfileResume.objects.create(
            profile=self.profile,
            parsed_text=text,
            resume_text_embedding_source=text,
            parsing_status=ProfileResume.ParsingStatus.SUCCEEDED,
            is_active=True,
        )

    def test_process_resume_persists_semantic_fields_and_cache_hash(self):
        resume = self.create_resume("Python Django Postgres Docker K8s CI/CD pipelines")

        result = process_profile_resume_semantics(
            resume,
            use_model=False,
            allow_semantic_mapping=False,
        )

        resume.refresh_from_db()
        self.assertEqual(result["status"], SEMANTIC_STATUS_SUCCEEDED)
        self.assertEqual(resume.semantic_resume_version, SEMANTIC_RESUME_VERSION)
        self.assertTrue(resume.semantic_resume_content_hash)
        self.assertIn("python", resume.extracted_skills)
        self.assertIn("django", resume.extracted_tools)
        self.assertIn("kubernetes", resume.extracted_tools)
        self.assertIn("devops", resume.extracted_domains)
        self.assertGreater(resume.semantic_resume_confidence, 0.0)

        second = process_profile_resume_semantics(
            resume,
            use_model=False,
            allow_semantic_mapping=False,
        )

        self.assertEqual(second["status"], SEMANTIC_STATUS_SKIPPED)

    @override_settings(LLM_ENRICHMENT_ENABLED=True)
    @patch("ai.llm.enrichment.enrich_resume_text")
    def test_process_resume_persists_llm_business_family_metadata(self, mock_llm_enrich):
        mock_llm_enrich.return_value = SimpleNamespace(
            as_dict=lambda: {
                "target_roles": ["IT Helpdesk Officer"],
                "canonical_role": "Technicien support informatique",
                "skills": ["Support utilisateur"],
                "tools": ["Windows", "TCP/IP"],
                "domains": ["support IT"],
                "business_families": ["it_network_support"],
                "family_confidence": 0.91,
                "confidence": 0.92,
                "provider": "ollama",
                "model": "llama3.2:3b",
            }
        )
        resume = self.create_resume("Support utilisateurs Windows TCP/IP et diagnostic materiel")

        result = process_profile_resume_semantics(
            resume,
            use_model=False,
            allow_semantic_mapping=False,
            force=True,
        )

        resume.refresh_from_db()
        self.assertEqual(result["business_families"], ["it_network_support"])
        self.assertEqual(result["canonical_role"], "Technicien support informatique")
        self.assertEqual(resume.semantic_resume_metadata["business_families"], ["it_network_support"])
        self.assertEqual(resume.semantic_resume_metadata["family_confidence"], 0.91)
        self.assertEqual(
            resume.semantic_resume_metadata["llm_enrichment"]["business_families"],
            ["it_network_support"],
        )

    @override_settings(LLM_ENRICHMENT_ENABLED=True)
    @patch("ai.llm.enrichment.enrich_resume_text")
    def test_office_admin_cv_overrides_customer_support_family(self, mock_llm_enrich):
        mock_llm_enrich.return_value = SimpleNamespace(
            as_dict=lambda: {
                "target_roles": ["Assistante de Bureau"],
                "canonical_role": "Assistante de Bureau",
                "skills": ["Organisation", "Communication"],
                "tools": [],
                "domains": ["Administration"],
                "business_families": ["customer_support"],
                "family_confidence": 1.0,
                "confidence": 1.0,
            }
        )
        resume = self.create_resume(
            "Assistante de bureau junior. Classement et archivage des dossiers, "
            "préparation de courriers et suivi administratif."
        )

        result = process_profile_resume_semantics(
            resume,
            use_model=False,
            allow_semantic_mapping=False,
            force=True,
        )

        resume.refresh_from_db()
        self.assertEqual(result["business_families"], ["administration"])
        self.assertEqual(resume.semantic_resume_metadata["business_families"], ["administration"])

    def test_embedding_features_prioritize_structured_resume_signals_over_raw_text(self):
        resume = self.create_resume("Raw CV says Python Django Postgres Docker K8s")
        process_profile_resume_semantics(resume, use_model=False, allow_semantic_mapping=False)

        features = build_user_features(self.profile)
        text = build_user_embedding_text(features)

        self.assertIn("resume extracted skills: python", text)
        self.assertIn("resume extracted tools:", text)
        self.assertNotIn("resume: Raw CV", text)

    def test_user_entered_skills_are_not_overwritten(self):
        self.profile.competences = ["Accounting"]
        self.profile.save(update_fields=["competences"])
        resume = self.create_resume("Python Django PostgreSQL")
        process_profile_resume_semantics(resume, use_model=False, allow_semantic_mapping=False)

        self.profile.refresh_from_db()
        features = build_user_features(self.profile)

        self.assertEqual(self.profile.competences, ["Accounting"])
        self.assertEqual(features["profile_skills"], ["Accounting"])
        self.assertIn("Accounting", features["skills"])
        self.assertIn("python", features["skills"])

    def test_empty_resume_is_safe(self):
        resume = self.create_resume("")

        result = process_profile_resume_semantics(resume, use_model=False)

        resume.refresh_from_db()
        self.assertEqual(result["status"], "EMPTY")
        self.assertEqual(resume.extracted_skills, [])
        self.assertEqual(resume.semantic_resume_confidence, 0.0)

    def test_runtime_is_bounded_for_noisy_cv(self):
        resume = self.create_resume(("Python Django Docker Kubernetes " * 1000) + "noise " * 1000)
        started = time.monotonic()

        process_profile_resume_semantics(resume, use_model=False, allow_semantic_mapping=False)

        self.assertLess(time.monotonic() - started, 2.0)

    def test_no_n_plus_one_for_feature_building(self):
        resume = self.create_resume("Python Django PostgreSQL")
        process_profile_resume_semantics(resume, use_model=False, allow_semantic_mapping=False)
        profile = type(self.profile).objects.get(pk=self.profile.pk)

        with self.assertNumQueries(1):
            features = build_user_features(profile)

        self.assertIn("python", features["skills"])

    @patch("users.resume_semantic.service.extract_skill_candidates")
    def test_process_resume_metadata_keeps_rejected_candidate_analytics_out_of_raw_skill_storage(
        self,
        mock_extract_skill_candidates,
    ):
        resume = self.create_resume("React et développer un portefeuille de clients")
        mock_extract_skill_candidates.return_value = [
            SkillCandidate(text="React", source="lexical", confidence=0.9),
            SkillCandidate(
                text="et développer un portefeuille de clients",
                source="escoxlmr",
                confidence=0.8,
            ),
            SkillCandidate(text="opportunités", source="escoxlmr", confidence=0.7),
        ]

        result = process_profile_resume_semantics(
            resume,
            use_model=False,
            allow_semantic_mapping=False,
            force=True,
        )

        resume.refresh_from_db()
        self.assertEqual(result["status"], SEMANTIC_STATUS_SUCCEEDED)
        self.assertEqual(resume.extracted_raw_skills, ["React"])
        self.assertEqual(len(resume.semantic_resume_metadata["rejected_raw_candidates"]), 2)
        self.assertEqual(
            [item["reason"] for item in resume.semantic_resume_metadata["rejected_raw_candidates"]],
            ["phrase_fragment", "generic_business_term"],
        )
