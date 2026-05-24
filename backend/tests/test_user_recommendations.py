from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ai.esco_mapper import clear_esco_mapper_cache, map_role_to_esco, map_skill_to_esco
from ai.models import ESCOOccupation
from ai.embeddings import (
    MAX_RESUME_EMBEDDING_TEXT_CHARS,
    build_user_embedding,
    build_user_embedding_text,
    build_user_features_hash,
    get_current_profile_embedding_model,
    get_or_build_profile_embedding,
)
from ai.recommendation_service import get_score_label, rank_opportunities
from ai.user_features import build_user_features
from users.models import ProfileResume, Utilisateur


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
            filtered = [
                resume
                for resume in filtered
                if getattr(resume, key, None) == expected
            ]
        return FakeResumeQuerySet(filtered)


class UserFeatureBuilderTests(SimpleTestCase):
    def test_build_user_features_normalizes_partial_profile(self):
        profile = SimpleNamespace(
            competences="Python, Django, python,  ",
            domaines_interet=["AI", "Backend Developer"],
            target_roles=["Backend Developer", "", "Backend Developer"],
            niveau_experience="JUNIOR",
            preferred_locations=[" Tunis "],
            remote_preference="REMOTE",
            employment_types=["FULL_TIME", "CONTRACT", "FULL_TIME"],
            compensation_expectation="45000",
            compensation_min_expectation="40000",
            compensation_max_expectation="50000",
        )

        self.assertEqual(
            build_user_features(profile),
            {
                "skills": ["Python", "Django"],
                "profile_skills": ["Python", "Django"],
                "semantic_resume_skills": [],
                "semantic_resume_domains": [],
                "semantic_resume_tools": [],
                "semantic_resume_languages": [],
                "semantic_resume_confidence": 0.0,
                "semantic_resume_business_families": [],
                "semantic_resume_family_confidence": 0.0,
                "semantic_resume_canonical_role": "",
                "semantic_resume_target_roles": [],
                "profile_business_families": [],
                "profile_family_confidence": 0.0,
                "roles": ["Backend Developer", "AI"],
                "target_roles": ["Backend Developer"],
                "interests": ["AI", "Backend Developer"],
                "experience_level": "JUNIOR",
                "experience_years": None,
                "locations": ["Tunis"],
                "location": "Tunis",
                "remote": "REMOTE",
                "work_modes": [],
                "employment_types": ["FULL_TIME", "CONTRACT"],
                "salary": 45000,
                "salary_min": 40000,
                "salary_max": 50000,
                "salary_currency": "",
                "salary_period": "",
            },
        )

    def test_build_user_features_handles_missing_fields(self):
        features = build_user_features(SimpleNamespace())

        self.assertEqual(features["skills"], [])
        self.assertEqual(features["profile_skills"], [])
        self.assertEqual(features["semantic_resume_skills"], [])
        self.assertEqual(features["semantic_resume_domains"], [])
        self.assertEqual(features["semantic_resume_tools"], [])
        self.assertEqual(features["semantic_resume_languages"], [])
        self.assertEqual(features["semantic_resume_confidence"], 0.0)
        self.assertEqual(features["semantic_resume_business_families"], [])
        self.assertEqual(features["semantic_resume_family_confidence"], 0.0)
        self.assertEqual(features["profile_business_families"], [])
        self.assertEqual(features["profile_family_confidence"], 0.0)
        self.assertEqual(features["roles"], [])
        self.assertEqual(features["target_roles"], [])
        self.assertEqual(features["interests"], [])
        self.assertEqual(features["experience_level"], "")
        self.assertEqual(features["experience_years"], None)
        self.assertEqual(features["work_modes"], [])
        self.assertEqual(features["salary"], None)
        self.assertEqual(features["salary_min"], None)
        self.assertEqual(features["salary_max"], None)
        self.assertEqual(features["salary_currency"], "")
        self.assertEqual(features["salary_period"], "")
        self.assertNotIn("resume_text", features)

    def test_build_user_features_reads_llm_resume_business_family(self):
        profile = SimpleNamespace(
            competences=["Windows"],
            domaines_interet=[],
            target_roles=["Technicien support informatique"],
            niveau_experience="JUNIOR",
            preferred_locations=[],
            remote_preference="",
            employment_types=[],
            compensation_expectation=None,
            resumes=FakeResumeManager(
                [
                    SimpleNamespace(
                        is_active=True,
                        parsed_text="Support utilisateurs Windows et TCP/IP",
                        extracted_skills=["Support utilisateur"],
                        extracted_domains=[],
                        extracted_tools=["Windows"],
                        extracted_languages=["fr"],
                        semantic_resume_confidence=0.91,
                        semantic_resume_status="SUCCEEDED",
                        semantic_resume_metadata={
                            "business_families": ["it_network_support"],
                            "family_confidence": 0.9,
                            "canonical_role": "Technicien support informatique",
                            "target_roles": ["IT Helpdesk Officer"],
                        },
                    )
                ]
            ),
        )

        features = build_user_features(profile)

        self.assertEqual(features["profile_business_families"], ["it_network_support"])
        self.assertEqual(features["profile_family_confidence"], 0.9)
        self.assertEqual(features["semantic_resume_canonical_role"], "Technicien support informatique")
        self.assertIn("IT Helpdesk Officer", features["roles"])

    def test_build_user_features_includes_only_active_resume_parsed_text(self):
        profile = SimpleNamespace(
            competences=["Python"],
            domaines_interet=[],
            target_roles=["Backend Developer"],
            niveau_experience="SENIOR",
            preferred_locations=[],
            remote_preference="",
            employment_types=[],
            compensation_expectation=None,
            resumes=FakeResumeManager(
                [
                    SimpleNamespace(is_active=False, parsed_text="Inactive resume"),
                    SimpleNamespace(is_active=True, parsed_text="Active backend CV"),
                ]
            ),
        )

        features = build_user_features(profile)

        self.assertEqual(features["resume_text"], "Active backend CV")

    def test_build_user_features_ignores_inactive_resume(self):
        profile = SimpleNamespace(
            resumes=FakeResumeManager(
                [SimpleNamespace(is_active=False, parsed_text="Inactive resume")]
            )
        )

        self.assertNotIn("resume_text", build_user_features(profile))


class UserFeatureResumeDatabaseTests(TestCase):
    def test_active_resume_lookup_is_bounded_and_lightweight(self):
        user = Utilisateur.objects.create_user(
            username="resume_query_check",
            email="resume_query_check@example.com",
            password="x",
        )
        profile = user.profil
        ProfileResume.objects.create(
            profile=profile,
            is_active=False,
            parsed_text="Inactive CV",
            metadata={"large": "ignored"},
        )
        ProfileResume.objects.create(
            profile=profile,
            is_active=True,
            parsed_text="Active Django CV",
            metadata={"large": "ignored"},
        )
        profile = type(profile).objects.get(pk=profile.pk)

        with CaptureQueriesContext(connection) as ctx:
            features = build_user_features(profile)

        self.assertEqual(features["resume_text"], "Active Django CV")
        self.assertEqual(len(ctx.captured_queries), 1)
        sql = ctx.captured_queries[0]["sql"]
        self.assertIn('"parsed_text"', sql)
        self.assertIn('"profile_id"', sql)
        self.assertNotIn('"file"', sql)
        self.assertNotIn('"metadata"', sql)


class UserEmbeddingTests(SimpleTestCase):
    def test_build_user_embedding_generates_from_feature_text(self):
        features = {
            "skills": ["Python", "Django"],
            "roles": ["Backend Developer"],
            "experience_level": "JUNIOR",
            "location": "Tunis",
            "remote": "REMOTE",
            "employment_types": ["FULL_TIME"],
            "salary": 45000,
        }

        with patch("ai.embeddings.generate_embedding", return_value=[0.1, 0.2]) as mocked:
            embedding = build_user_embedding(features)

        self.assertEqual(embedding, [0.1, 0.2])
        text = mocked.call_args.args[0]
        self.assertIn("skills: Python, Django", text)
        self.assertIn("target roles: Backend Developer", text)
        self.assertIn("salary expectation: 45000", text)

    def test_build_user_embedding_returns_empty_for_empty_features(self):
        with patch("ai.embeddings.generate_embedding") as mocked:
            self.assertEqual(build_user_embedding({}), [])

        mocked.assert_not_called()

    def test_build_user_embedding_text_is_stable(self):
        text = build_user_embedding_text(
            {
                "skills": ["React"],
                "roles": [],
                "experience_level": "",
                "location": "Remote",
                "remote": "REMOTE",
                "employment_types": [],
                "salary": None,
            }
        )

        self.assertEqual(text, "skills: React\nlocation: Remote\nremote preference: REMOTE")

    def test_build_user_embedding_text_includes_active_resume_text(self):
        features = {
            "skills": ["Python", "Django"],
            "roles": ["Backend Developer"],
            "resume_text": "Built APIs with Django and PostgreSQL.",
        }

        text = build_user_embedding_text(features)

        self.assertEqual(
            text,
            "skills: Python, Django\n"
            "target roles: Backend Developer\n"
            "resume: Built APIs with Django and PostgreSQL.",
        )

    def test_build_user_embedding_text_preserves_multilingual_resume_content(self):
        text = build_user_embedding_text(
            {
                "skills": ["Python"],
                "resume_text": "Développeur backend. خبرة في Django و APIs.",
            }
        )

        self.assertIn("Développeur backend", text)
        self.assertIn("خبرة في Django", text)

    def test_build_user_embedding_text_sanitizes_and_truncates_resume_text(self):
        noisy_resume = "\x00Python\n\n\tDjango" + (" a" * 5000)

        text = build_user_embedding_text({"resume_text": noisy_resume})
        resume_text = text.removeprefix("resume: ")

        self.assertNotIn("\x00", resume_text)
        self.assertNotIn("\n", resume_text)
        self.assertLessEqual(len(resume_text), MAX_RESUME_EMBEDDING_TEXT_CHARS)

    def test_build_user_embedding_text_resume_output_is_deterministic(self):
        features = {
            "skills": ["Python"],
            "resume_text": "Backend\x00 developer\n\nPython",
        }

        self.assertEqual(
            build_user_embedding_text(features),
            build_user_embedding_text(features),
        )

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_get_or_build_profile_embedding_uses_cache_when_features_are_unchanged(self):
        profile = SimpleNamespace(
            competences=["Python"],
            target_roles=["Backend Developer"],
            domaines_interet=[],
            niveau_experience="JUNIOR",
            preferred_locations=["Tunis"],
            remote_preference="REMOTE",
            employment_types=["FULL_TIME"],
            compensation_expectation=45000,
            embedding=[0.1, 0.2],
            embedding_features_hash="",
            embedding_model=get_current_profile_embedding_model(),
            embedding_dimensions=2,
            embedding_updated_at=timezone.now(),
            embedding_content_hash="",
        )
        content_hash = build_user_features_hash(build_user_features(profile))
        profile.embedding_features_hash = content_hash
        profile.embedding_content_hash = content_hash

        with patch("ai.embeddings.build_user_embedding") as mocked:
            embedding = get_or_build_profile_embedding(profile)

        self.assertEqual(embedding, [0.1, 0.2])
        mocked.assert_not_called()

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_get_or_build_profile_embedding_rebuilds_when_features_changed(self):
        class FakeProfile(SimpleNamespace):
            def save(self, update_fields=None):
                self.saved_update_fields = update_fields

        profile = FakeProfile(
            competences=["Python"],
            target_roles=["Backend Developer"],
            domaines_interet=[],
            niveau_experience="JUNIOR",
            preferred_locations=["Tunis"],
            remote_preference="REMOTE",
            employment_types=["FULL_TIME"],
            compensation_expectation=45000,
            embedding=[0.1, 0.2],
            embedding_features_hash="stale",
            embedding_model=get_current_profile_embedding_model(),
            embedding_dimensions=2,
            embedding_updated_at=timezone.now(),
            embedding_content_hash="stale",
        )

        with patch("ai.embeddings.build_user_embedding", return_value=[0.4, 0.5]) as mocked:
            embedding = get_or_build_profile_embedding(profile)

        self.assertEqual(embedding, [0.4, 0.5])
        mocked.assert_called_once()
        self.assertIn("embedding_features_hash", profile.saved_update_fields)
        self.assertIn("embedding_content_hash", profile.saved_update_fields)
        self.assertEqual(profile.embedding_dimensions, 2)


class RecommendationRankingTests(SimpleTestCase):
    databases = {"default"}

    def test_rank_opportunities_orders_by_cosine_similarity(self):
        low = SimpleNamespace(id=1, embedding_vector=[0.0, 1.0], date_publication=date(2026, 1, 1))
        high = SimpleNamespace(id=2, embedding_vector=[0.9, 0.1], date_publication=date(2026, 1, 1))
        medium = SimpleNamespace(id=3, embedding_vector=[0.6, 0.4], date_publication=date(2026, 1, 2))

        ranked = rank_opportunities([1.0, 0.0], [low, high, medium], top_k=2)

        self.assertEqual([item.id for item in ranked], [2, 3])
        self.assertGreater(ranked[0].match_score, ranked[1].match_score)

    def test_rank_opportunities_skips_missing_or_incompatible_vectors(self):
        ranked = rank_opportunities(
            [1.0, 0.0],
            [
                SimpleNamespace(id=1, embedding_vector=None),
                SimpleNamespace(id=2, embedding_vector=[1.0, 0.0, 0.0]),
                SimpleNamespace(id=3, embedding_vector=[1.0, 0.0]),
            ],
        )

        self.assertEqual([item.id for item in ranked], [3])

    def test_rank_opportunities_supports_dict_inputs_without_mutation(self):
        source = {"id": 1, "embedding_vector": [1.0, 0.0]}

        ranked = rank_opportunities([1.0, 0.0], [source])

        self.assertAlmostEqual(ranked[0]["match_score"], 0.7)
        self.assertEqual(ranked[0]["semantic_score"], 1.0)
        self.assertEqual(ranked[0]["business_score"], 0.0)
        self.assertEqual(ranked[0]["feedback_score"], 0.0)
        self.assertEqual(ranked[0]["score_label"], "Good match")
        self.assertEqual(ranked[0]["reason"], [])
        self.assertNotIn("match_score", source)

    def test_rank_opportunities_adds_business_rules_and_reasons(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Remote Python Backend Developer",
            ville="Tunis",
            contract_type="Full time",
            availability="Remote",
            experience_min=1,
            experience_max=3,
            skills=["Python", "Django"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": ["Python", "React"],
            "roles": ["Backend Developer"],
            "experience_level": "JUNIOR",
            "locations": ["Tunis"],
            "location": "Tunis",
            "remote": "REMOTE",
            "employment_types": ["FULL_TIME"],
            "salary": None,
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(len(ranked), 1)
        self.assertGreater(ranked[0].match_score, ranked[0].semantic_score)
        self.assertIn("Python", ranked[0].reason)
        self.assertIn("Remote match", ranked[0].reason)
        self.assertIn("Experience match", ranked[0].reason)

    def test_rank_opportunities_uses_salary_as_lightweight_signal_when_available(self):
        aligned = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            ville="Tunis",
            salary="1800 - 2400 TND",
            skills=["React"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )
        below = SimpleNamespace(
            id=2,
            titre="Frontend Developer",
            ville="Tunis",
            salary="900 - 1200 TND",
            skills=["React"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": ["React"],
            "salary_min": 1700,
            "salary_max": 2200,
        }

        ranked = rank_opportunities([1.0, 0.0], [below, aligned], features=features)

        self.assertEqual(ranked[0].id, aligned.id)
        self.assertIn("Salary range aligned", ranked[0].reason)
        self.assertGreater(
            ranked[0].recommendation_debug["business_components"]["salary_bonus"],
            0,
        )
        self.assertLess(
            ranked[1].recommendation_debug["business_components"]["salary_bonus"],
            0,
        )

    def test_rank_opportunities_uses_work_mode_preferences_for_remote_bonus(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            ville="Tunis",
            contract_type="Full time",
            availability="Remote",
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "work_modes": ["REMOTE"],
            "remote": "",
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(ranked[0].business_score, 0.08)
        self.assertIn("Remote match", ranked[0].reason)

    def test_rank_opportunities_prefers_work_modes_over_legacy_remote_value(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Hybrid Backend Developer",
            ville="Tunis",
            contract_type="Full time",
            availability="Hybrid",
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "work_modes": ["HYBRID"],
            "remote": "REMOTE",
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(ranked[0].business_score, 0.08)
        self.assertIn("Hybrid match", ranked[0].reason)
        self.assertNotIn("Remote match", ranked[0].reason)

    def test_rank_opportunities_rejects_full_time_for_internship_only_profiles(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            contract_type="CDI",
            normalized_contract_types=["CDI"],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["INTERNSHIP"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(ranked, [])

    def test_rank_opportunities_rejects_internship_for_full_time_only_profiles(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Intern",
            type_opportunite="STAGE",
            normalized_contract_types=["INTERNSHIP"],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["FULL_TIME"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(ranked, [])

    def test_rank_opportunities_keeps_mixed_contracts_for_flexible_profiles(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            contract_type="CDI - Stage",
            normalized_contract_types=["CDI", "INTERNSHIP"],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["INTERNSHIP", "FULL_TIME"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual([item.id for item in ranked], [1])

    def test_rank_opportunities_keeps_unknown_contracts_for_strict_profiles(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            contract_type="",
            normalized_contract_types=[],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["INTERNSHIP"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual([item.id for item in ranked], [1])

    def test_rank_opportunities_parses_noisy_mixed_contracts_as_flexible(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            contract_type="CDI-Stage",
            normalized_contract_types=[],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["INTERNSHIP"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual([item.id for item in ranked], [1])

    def test_rank_opportunities_parses_permanent_as_full_time_incompatible(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            contract_type="Permanent contract",
            normalized_contract_types=[],
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "employment_types": ["INTERNSHIP"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(ranked, [])

    def test_rank_opportunities_penalizes_scores_without_metier_evidence(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Stage Marketing Digital",
            ville="Tunis",
            contract_type="Stage",
            type_opportunite="STAGE",
            experience_min=0,
            experience_max=1,
            skills=[],
            embedding_vector=[0.4, 0.916515],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": ["React"],
            "roles": ["Frontend Developer"],
            "locations": ["Tunis"],
            "location": "Tunis",
            "employment_types": ["INTERNSHIP"],
            "experience_level": "DEBUTANT",
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].semantic_score, 0.4, places=4)
        self.assertAlmostEqual(ranked[0].business_score, 0.2)
        self.assertAlmostEqual(ranked[0].match_score, 0.26, places=4)

    def test_rank_opportunities_does_not_penalize_skill_evidence(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            skills=["React"],
            embedding_vector=[0.4, 0.916515],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": ["React"],
            "roles": ["Backend Developer"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].semantic_score, 0.4, places=4)
        self.assertAlmostEqual(ranked[0].business_score, 0.025)
        self.assertAlmostEqual(ranked[0].match_score, 0.31, places=4)
        self.assertIn("React", ranked[0].reason)

    def test_rank_opportunities_does_not_penalize_strong_semantic_evidence(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Product Analyst",
            skills=[],
            embedding_vector=[0.65, 0.759935],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": ["React"],
            "roles": ["Frontend Developer"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].semantic_score, 0.65, places=4)
        self.assertAlmostEqual(ranked[0].business_score, 0.0)
        self.assertAlmostEqual(ranked[0].match_score, 0.455, places=4)

    def test_rank_opportunities_penalizes_duplicate_company_results(self):
        same_company_one = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            organisation_nom="Acme",
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        same_company_two = SimpleNamespace(
            id=2,
            titre="Backend Developer Remote",
            organisation_nom="Acme",
            embedding_vector=[0.99, 0.01],
            date_publication=date(2026, 1, 1),
        )
        other_company = SimpleNamespace(
            id=3,
            titre="Data Engineer",
            organisation_nom="OtherCo",
            embedding_vector=[0.98, 0.02],
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities(
            [1.0, 0.0],
            [same_company_one, same_company_two, other_company],
            top_k=2,
        )

        self.assertEqual([item.id for item in ranked], [1, 3])
        self.assertGreater(getattr(same_company_two, "diversity_penalty", 0), 0)

    def test_rank_opportunities_suppresses_exact_duplicate_results(self):
        duplicate_one = SimpleNamespace(
            id=1,
            titre="Junior Frontend Developer",
            organisation_nom="Linedata",
            ville="Tunis",
            type_opportunite="EMPLOI",
            embedding_vector=[1.0, 0.0],
            date_publication=date(2026, 1, 1),
        )
        duplicate_two = SimpleNamespace(
            id=2,
            titre="Junior Frontend Developer",
            organisation_nom="Linedata",
            ville="Tunis",
            type_opportunite="EMPLOI",
            embedding_vector=[0.99, 0.01],
            date_publication=date(2026, 1, 2),
        )

        ranked = rank_opportunities([1.0, 0.0], [duplicate_one, duplicate_two])

        self.assertEqual(len(ranked), 1)
        self.assertTrue(getattr(duplicate_one, "duplicate_suppressed", False) or getattr(duplicate_two, "duplicate_suppressed", False))

    def test_rank_opportunities_boosts_precise_onsite_location_match(self):
        sousse = SimpleNamespace(
            id=1,
            titre="Comptable",
            organisation_nom="SousseCo",
            ville="Sousse",
            skills=["Comptabilité"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )
        tunis = SimpleNamespace(
            id=2,
            titre="Comptable",
            organisation_nom="TunisCo",
            ville="Tunis",
            skills=["Comptabilité"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 2),
        )
        features = {
            "roles": ["Comptable"],
            "target_roles": ["Comptable"],
            "skills": ["Comptabilité"],
            "profile_skills": ["Comptabilité"],
            "locations": ["Sousse"],
            "work_modes": ["ON_SITE"],
        }

        ranked = rank_opportunities([1.0, 0.0], [tunis, sousse], features=features)

        self.assertEqual(ranked[0].id, sousse.id)
        self.assertGreater(
            ranked[0].recommendation_debug["business_components"]["strict_location_adjustment"],
            0,
        )
        self.assertLess(
            ranked[1].recommendation_debug["business_components"]["strict_location_adjustment"],
            0,
        )

    def test_rank_opportunities_penalizes_single_generic_skill_outside_family(self):
        generic = SimpleNamespace(
            id=1,
            titre="Développeur Informatique Senior",
            organisation_nom="GenericCo",
            ville="Tunis",
            skills=["JavaScript"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )
        frontend = SimpleNamespace(
            id=2,
            titre="Frontend React Developer",
            organisation_nom="FrontendCo",
            ville="Tunis",
            skills=["React", "JavaScript"],
            embedding_vector=[0.75, 0.25],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": ["React", "JavaScript"],
            "profile_skills": ["React", "JavaScript"],
        }

        ranked = rank_opportunities([1.0, 0.0], [generic, frontend], features=features)

        self.assertEqual(ranked[0].id, frontend.id)
        self.assertLessEqual(ranked[1].match_score, 0.49)

    def test_rank_opportunities_boosts_jobs_similar_to_applications(self):
        candidate = SimpleNamespace(
            id=1,
            titre="Data Engineer",
            organisation_nom="DataCo",
            skills=["Python"],
            embedding_vector=[0.8, 0.2],
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities(
            [1.0, 0.0],
            [candidate],
            feedback={"applied_skills": ["Python"], "applied_embeddings": []},
        )

        self.assertEqual(ranked[0].feedback_score, 0.05)
        self.assertIn("Similar to your applications", ranked[0].reason)

    def test_partial_profile_ranking_works_without_user_embedding(self):
        candidate = SimpleNamespace(
            id=1,
            titre="Frontend Developer",
            organisation_nom="WebCo",
            ville="Tunis",
            contract_type="Full time",
            application_count=4,
            embedding_vector=None,
            date_publication=date(2026, 1, 1),
        )
        features = {
            "skills": [],
            "roles": [],
            "experience_level": "",
            "locations": ["Tunis"],
            "location": "Tunis",
            "remote": "",
            "employment_types": ["FULL_TIME"],
            "salary": None,
        }

        ranked = rank_opportunities([], [candidate], features=features, mode="partial")

        self.assertEqual([item.id for item in ranked], [1])
        self.assertGreater(ranked[0].match_score, 0)
        self.assertIn("Location match: Tunis", ranked[0].reason)

    def test_score_labels_are_bucketed_for_ux(self):
        self.assertEqual(get_score_label(0.9), "Top match")
        self.assertEqual(get_score_label(0.7), "Good match")
        self.assertEqual(get_score_label(0.4), "Worth a look")
        self.assertEqual(get_score_label(0.0, is_fallback=True), "Recent")


class ESCOMapperCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ESCOOccupation.objects.bulk_create(
            [
                ESCOOccupation(
                    uri="esco:frontend_developer",
                    preferred_label="Frontend Developer",
                    family="frontend_engineering",
                    isco_group="2512",
                    alternate_labels=["UI Engineer", "Frontend Engineer"],
                    related_skills=["react", "typescript", "javascript"],
                ),
                ESCOOccupation(
                    uri="esco:data_scientist",
                    preferred_label="Data Scientist",
                    family="data_ai",
                    isco_group="2521",
                    alternate_labels=["ML Engineer", "AI Engineer"],
                    related_skills=["machine learning", "tensorflow", "pandas"],
                ),
            ]
        )

    def setUp(self):
        clear_esco_mapper_cache()

    def tearDown(self):
        clear_esco_mapper_cache()

    def test_map_role_to_esco_is_case_insensitive_and_cached(self):
        with CaptureQueriesContext(connection) as first_lookup:
            occupation = map_role_to_esco("ui engineer")

        self.assertEqual(occupation.preferred_label, "Frontend Developer")
        self.assertEqual(len(first_lookup), 1)

        with CaptureQueriesContext(connection) as second_lookup:
            occupation = map_role_to_esco("UI ENGINEER")

        self.assertEqual(occupation.preferred_label, "Frontend Developer")
        self.assertEqual(len(second_lookup), 0)

    def test_map_skill_to_esco_is_cached(self):
        with CaptureQueriesContext(connection) as first_lookup:
            payload = map_skill_to_esco("TypeScript")

        self.assertEqual(payload["family"], "frontend_engineering")
        self.assertEqual(payload["occupation"], "Frontend Developer")
        self.assertEqual(len(first_lookup), 1)

        with CaptureQueriesContext(connection) as second_lookup:
            payload = map_skill_to_esco("typescript")

        self.assertEqual(payload["family"], "frontend_engineering")
        self.assertEqual(len(second_lookup), 0)

    def test_empty_dataset_returns_none_without_crashing(self):
        ESCOOccupation.objects.all().delete()
        clear_esco_mapper_cache()

        self.assertIsNone(map_role_to_esco("Frontend Developer"))
        self.assertIsNone(map_skill_to_esco("react"))


class ESCORecommendationBonusTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ESCOOccupation.objects.bulk_create(
            [
                ESCOOccupation(
                    uri="esco:frontend_developer",
                    preferred_label="Frontend Developer",
                    family="frontend_engineering",
                    isco_group="2512",
                    alternate_labels=["UI Engineer", "Front-End Engineer", "Frontend Engineer"],
                    related_skills=["react", "typescript", "javascript", "tailwind"],
                ),
                ESCOOccupation(
                    uri="esco:backend_developer",
                    preferred_label="Backend Developer",
                    family="backend_engineering",
                    isco_group="2512",
                    alternate_labels=["API Developer", "Server-side Developer"],
                    related_skills=["python", "django", "postgresql", "api"],
                ),
                ESCOOccupation(
                    uri="esco:data_scientist",
                    preferred_label="Data Scientist",
                    family="data_ai",
                    isco_group="2521",
                    alternate_labels=["ML Engineer", "AI Engineer"],
                    related_skills=["tensorflow", "pandas", "nlp", "machine learning"],
                ),
            ]
        )

    def setUp(self):
        clear_esco_mapper_cache()

    def tearDown(self):
        clear_esco_mapper_cache()

    @staticmethod
    def _vector_with_similarity(similarity):
        return [float(similarity), max(0.0, 1.0 - float(similarity) ** 2) ** 0.5]

    def test_ui_engineer_gains_small_frontend_family_bonus(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Senior UI Engineer",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.62),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": [],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].semantic_score, 0.62, places=4)
        self.assertAlmostEqual(ranked[0].business_score, 0.03, places=4)
        self.assertAlmostEqual(ranked[0].match_score, 0.47, places=4)
        self.assertEqual(ranked[0].reason, [])

    def test_ml_engineer_gains_small_data_ai_family_bonus(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Principal ML Engineer",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.63),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Data Scientist"],
            "target_roles": ["Data Scientist"],
            "skills": [],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].business_score, 0.03, places=4)
        self.assertAlmostEqual(ranked[0].match_score, 0.477, places=4)

    def test_frontend_profile_gets_no_esco_bonus_for_seo_webmaster_role(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="SEO Webmaster",
            skills=["SEO", "Google Analytics"],
            embedding_vector=self._vector_with_similarity(0.72),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": ["React", "TypeScript"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].semantic_score, 0.72, places=4)
        self.assertAlmostEqual(ranked[0].business_score, 0.0, places=4)
        self.assertAlmostEqual(ranked[0].match_score, 0.504, places=4)

    def test_exact_backend_matches_keep_existing_business_score(self):
        opportunity = SimpleNamespace(
            id=1,
            titre="Python Backend Developer",
            skills=["Python", "Django"],
            embedding_vector=self._vector_with_similarity(0.40),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Backend Developer"],
            "target_roles": ["Backend Developer"],
            "skills": ["Python"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertAlmostEqual(ranked[0].business_score, 0.085, places=4)
        self.assertAlmostEqual(ranked[0].match_score, 0.417, places=4)
        self.assertIn("Python", ranked[0].reason)
        self.assertIn("Backend Developer", ranked[0].reason)

    def test_support_it_role_does_not_match_customer_support_title(self):
        customer_support = SimpleNamespace(
            id=1,
            titre="Customer Service Support",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.40),
            date_publication=date(2026, 1, 1),
        )
        it_support = SimpleNamespace(
            id=2,
            titre="IT Support Specialist",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.40),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "roles": ["Support IT"],
            "target_roles": ["Support IT"],
            "skills": ["Windows"],
        }

        ranked = rank_opportunities([1.0, 0.0], [customer_support, it_support], features=features)

        by_id = {item.id: item for item in ranked}
        self.assertNotIn("Support IT", by_id[1].reason)
        self.assertIn("Support IT", by_id[2].reason)
        self.assertLess(by_id[1].business_score, by_id[2].business_score)

    @override_settings(JOBBERT_RERANK_ENABLED=True, JOBBERT_ALLOW_LIVE_FALLBACK=False)
    @patch("ai.recommendation_service.build_precomputed_jobbert_scores", return_value={1: 0.68})
    @patch("ai.recommendation_service.get_or_build_profile_jobbert_embedding", return_value=[1.0, 0.0])
    def test_jobbert_bonus_is_added_when_enabled(self, profile_embedding_mock, jobbert_scores_mock):
        opportunity = SimpleNamespace(
            id=1,
            titre="Junior Frontend Developer",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )
        features = {
            "_profile": SimpleNamespace(id=99),
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": ["React", "JavaScript"],
        }

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)

        self.assertEqual(profile_embedding_mock.call_count, 1)
        self.assertEqual(jobbert_scores_mock.call_count, 1)
        self.assertAlmostEqual(ranked[0].recommendation_debug["jobbert_score"], 0.68, places=4)
        self.assertAlmostEqual(ranked[0].recommendation_debug["jobbert_adjustment"], 0.08, places=4)
        self.assertIn("Strong semantic job match", ranked[0].reason)

    @override_settings(JOBBERT_RERANK_ENABLED=False, JOBBERT_ALLOW_LIVE_FALLBACK=False)
    @patch("ai.recommendation_service.build_precomputed_jobbert_scores", return_value={1: 0.68})
    @patch("ai.recommendation_service.get_or_build_profile_jobbert_embedding", return_value=[])
    def test_explicit_jobbert_profile_vector_enables_audit_ranking(self, profile_embedding_mock, jobbert_scores_mock):
        opportunity = SimpleNamespace(
            id=1,
            titre="Junior Frontend Developer",
            skills=[],
            embedding_vector=[],
            date_publication=date(2026, 1, 1),
        )
        features = {
            "_jobbert_profile_vector": [1.0, 0.0],
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": ["React", "JavaScript"],
        }

        ranked = rank_opportunities([], [opportunity], features=features, mode="partial")

        self.assertEqual(profile_embedding_mock.call_count, 0)
        self.assertEqual(jobbert_scores_mock.call_count, 1)
        self.assertAlmostEqual(ranked[0].recommendation_debug["jobbert_score"], 0.68, places=4)
        self.assertIn("Strong semantic job match", ranked[0].reason)

    def test_esco_bonus_stays_small_near_semantic_threshold(self):
        features = {
            "roles": ["Frontend Developer"],
            "target_roles": ["Frontend Developer"],
            "skills": [],
        }
        mapped_alias = SimpleNamespace(
            id=1,
            titre="UI Engineer",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )
        unmapped_title = SimpleNamespace(
            id=2,
            titre="Product Analyst",
            skills=[],
            embedding_vector=self._vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )

        mapped_ranked = rank_opportunities([1.0, 0.0], [mapped_alias], features=features)
        baseline_ranked = rank_opportunities([1.0, 0.0], [unmapped_title], features=features)

        self.assertAlmostEqual(mapped_ranked[0].business_score, 0.03, places=4)
        self.assertAlmostEqual(baseline_ranked[0].business_score, 0.0, places=4)
        self.assertLess(mapped_ranked[0].match_score - baseline_ranked[0].match_score, 0.05)
