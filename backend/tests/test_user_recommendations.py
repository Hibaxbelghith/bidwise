from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

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
        self.assertEqual(features["roles"], [])
        self.assertEqual(features["target_roles"], [])
        self.assertEqual(features["interests"], [])
        self.assertEqual(features["experience_level"], "")
        self.assertEqual(features["experience_years"], None)
        self.assertEqual(features["work_modes"], [])
        self.assertEqual(features["salary"], None)
        self.assertEqual(features["salary_currency"], "")
        self.assertEqual(features["salary_period"], "")
        self.assertNotIn("resume_text", features)

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
