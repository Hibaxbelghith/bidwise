from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from ai.embeddings import (
    build_profile_embedding_content_hash,
    build_user_features_hash,
    get_cached_profile_embedding_or_enqueue,
    get_current_profile_embedding_model,
    get_or_build_profile_embedding,
    profile_embedding_is_stale,
    profile_embedding_needs_refresh,
    validate_profile_embedding_vector,
)
from users.models import ProfileResume, Utilisateur
from users.serializers import ProfilUpdateSerializer
from users.tasks import generate_profile_embedding


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


def make_profile(**overrides):
    values = {
        "competences": ["Python", "Django"],
        "target_roles": ["Backend Developer"],
        "domaines_interet": ["HEALTHCARE"],
        "niveau_experience": "JUNIOR",
        "annees_experience": 2,
        "preferred_locations": ["Tunis"],
        "remote_preference": "REMOTE",
        "work_mode_preferences": ["REMOTE"],
        "employment_types": ["FULL_TIME"],
        "compensation_expectation": 1800,
        "resumes": FakeResumeManager(
            [SimpleNamespace(is_active=True, parsed_text="Backend Django APIs")]
        ),
        "embedding": [0.1, 0.2],
        "embedding_model": get_current_profile_embedding_model(),
        "embedding_dimensions": 2,
        "embedding_updated_at": timezone.now(),
        "embedding_content_hash": "",
        "embedding_features_hash": "",
    }
    values.update(overrides)
    profile = SimpleNamespace(**values)
    content_hash = build_profile_embedding_content_hash(profile)
    if not overrides.get("embedding_content_hash"):
        profile.embedding_content_hash = content_hash
    if not overrides.get("embedding_features_hash"):
        profile.embedding_features_hash = content_hash
    return profile


class ProfileEmbeddingMetadataTests(SimpleTestCase):
    def test_content_hash_is_stable_with_deterministic_ordering(self):
        left = {
            "skills": [" Python ", "python", "Django", ""],
            "target_roles": [" Backend Developer "],
            "interests": ["HEALTHCARE", "healthcare"],
            "locations": [" Tunis ", "tunis"],
            "work_modes": ["REMOTE", "remote"],
            "employment_types": ["FULL_TIME", "full_time"],
            "resume_text": "Backend Django APIs",
        }
        right = {
            "skills": ["django", "PYTHON"],
            "target_roles": ["backend developer"],
            "interests": ["healthcare"],
            "locations": ["tunis"],
            "work_modes": ["remote"],
            "employment_types": ["full_time"],
            "resume_text": "Backend   Django\nAPIs",
        }

        self.assertEqual(build_user_features_hash(left), build_user_features_hash(right))

    def test_content_hash_changes_when_cv_changes(self):
        profile = make_profile()
        original_hash = build_profile_embedding_content_hash(profile)
        profile.resumes = FakeResumeManager(
            [SimpleNamespace(is_active=True, parsed_text="Machine Learning NLP")]
        )

        self.assertNotEqual(original_hash, build_profile_embedding_content_hash(profile))

    def test_content_hash_changes_when_skills_change(self):
        original_hash = build_user_features_hash({"skills": ["Python"]})
        changed_hash = build_user_features_hash({"skills": ["Python", "Django"]})

        self.assertNotEqual(original_hash, changed_hash)

    def test_content_hash_is_unicode_stable(self):
        features = {
            "skills": ["Python"],
            "resume_text": "\u0645\u0647\u0646\u062f\u0633 Django D\u00e9veloppeur",
        }

        self.assertEqual(
            build_user_features_hash(features),
            build_user_features_hash(features.copy()),
        )

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_stale_detection_accepts_current_metadata(self):
        profile = make_profile()

        self.assertFalse(profile_embedding_needs_refresh(profile))
        self.assertFalse(profile_embedding_is_stale(profile))

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_stale_detection_rejects_missing_or_outdated_metadata(self):
        self.assertTrue(profile_embedding_needs_refresh(make_profile(embedding_model="")))
        self.assertTrue(profile_embedding_needs_refresh(make_profile(embedding_updated_at=None)))
        self.assertTrue(profile_embedding_needs_refresh(make_profile(embedding_content_hash="stale")))

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_stale_detection_rejects_dimension_mismatch(self):
        profile = make_profile(embedding_dimensions=384)

        self.assertTrue(profile_embedding_needs_refresh(profile))

    def test_valid_vector_acceptance(self):
        self.assertEqual(
            validate_profile_embedding_vector([1, "0.5"], expected_dimensions=2),
            [1.0, 0.5],
        )

    def test_invalid_vector_rejection(self):
        invalid_vectors = [
            [],
            [1, "bad"],
            [1, float("nan")],
            [1, float("inf")],
        ]

        for vector in invalid_vectors:
            with self.subTest(vector=vector):
                with self.assertRaises(ValueError):
                    validate_profile_embedding_vector(vector, expected_dimensions=2)

    def test_dimension_mismatch_rejection(self):
        with self.assertRaises(ValueError):
            validate_profile_embedding_vector([0.1], expected_dimensions=2)

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_invalid_generated_vector_is_not_stored(self):
        class FakeProfile(SimpleNamespace):
            def save(self, update_fields=None):
                self.saved_update_fields = update_fields

        base_profile = make_profile(
            embedding=[],
            embedding_model="",
            embedding_dimensions=None,
            embedding_updated_at=None,
            embedding_content_hash="",
        )
        profile = FakeProfile(**vars(base_profile))

        with patch("ai.embeddings.build_user_embedding", return_value=[0.1, float("nan")]):
            with self.assertRaises(ValueError):
                get_or_build_profile_embedding(profile)

        self.assertFalse(hasattr(profile, "saved_update_fields"))

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_stale_cached_lookup_enqueues_without_sync_generation(self):
        profile = make_profile(
            pk=123,
            embedding=[],
            embedding_model="",
            embedding_dimensions=None,
            embedding_updated_at=None,
            embedding_content_hash="",
        )

        with patch("ai.embeddings.build_user_embedding") as build_mock:
            with patch("ai.embeddings.enqueue_profile_embedding_refresh", return_value=True) as enqueue_mock:
                embedding = get_cached_profile_embedding_or_enqueue(profile)

        self.assertEqual(embedding, [])
        build_mock.assert_not_called()
        enqueue_mock.assert_called_once_with(123)


class ProfileEmbeddingTaskTests(TransactionTestCase):
    def create_profile(self):
        user = Utilisateur.objects.create_user(
            username="profile_embedding_task",
            email="profile_embedding_task@example.com",
            password="x",
        )
        profile = user.profil
        profile.competences = ["Python", "Django"]
        profile.target_roles = ["Backend Developer"]
        profile.domaines_interet = ["HEALTHCARE"]
        profile.niveau_experience = "JUNIOR"
        profile.annees_experience = 2
        profile.preferred_locations = ["Tunis"]
        profile.remote_preference = "REMOTE"
        profile.work_mode_preferences = ["REMOTE"]
        profile.employment_types = ["FULL_TIME"]
        profile.compensation_expectation = 1800
        profile.save()
        ProfileResume.objects.create(
            profile=profile,
            is_active=True,
            parsed_text="Backend Django APIs PostgreSQL",
        )
        return profile

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_celery_task_success_updates_embedding_metadata(self):
        profile = self.create_profile()

        with patch("users.tasks.build_user_embedding", return_value=[0.1, 0.2]):
            result = generate_profile_embedding.run(profile.pk)

        profile.refresh_from_db()
        self.assertEqual(result["status"], "updated")
        self.assertEqual(profile.embedding, [0.1, 0.2])
        self.assertEqual(profile.embedding_dimensions, 2)
        self.assertEqual(profile.embedding_model, get_current_profile_embedding_model())
        self.assertTrue(profile.embedding_content_hash)
        self.assertEqual(profile.embedding_features_hash, profile.embedding_content_hash)
        self.assertIsNotNone(profile.embedding_updated_at)

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_stale_profile_is_regenerated(self):
        profile = self.create_profile()
        profile.embedding = [0.9, 0.1]
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = 2
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = "stale"
        profile.embedding_features_hash = "stale"
        profile.save(
            update_fields=[
                "embedding",
                "embedding_model",
                "embedding_dimensions",
                "embedding_updated_at",
                "embedding_content_hash",
                "embedding_features_hash",
            ]
        )

        with patch("users.tasks.build_user_embedding", return_value=[0.4, 0.6]):
            result = generate_profile_embedding.run(profile.pk)

        profile.refresh_from_db()
        self.assertEqual(result["status"], "updated")
        self.assertEqual(profile.embedding, [0.4, 0.6])
        self.assertNotEqual(profile.embedding_content_hash, "stale")

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_non_stale_profile_is_skipped(self):
        profile = self.create_profile()
        content_hash = build_profile_embedding_content_hash(profile)
        profile.embedding = [0.1, 0.2]
        profile.embedding_model = get_current_profile_embedding_model()
        profile.embedding_dimensions = 2
        profile.embedding_updated_at = timezone.now()
        profile.embedding_content_hash = content_hash
        profile.embedding_features_hash = content_hash
        profile.save(
            update_fields=[
                "embedding",
                "embedding_model",
                "embedding_dimensions",
                "embedding_updated_at",
                "embedding_content_hash",
                "embedding_features_hash",
            ]
        )

        with patch("users.tasks.build_user_embedding") as mocked:
            result = generate_profile_embedding.run(profile.pk)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "fresh")
        mocked.assert_not_called()

    @override_settings(OPPORTUNITY_PGVECTOR_DIMENSIONS=2)
    def test_invalid_task_vector_is_rejected(self):
        profile = self.create_profile()

        with patch("users.tasks.build_user_embedding", return_value=[0.1, float("nan")]):
            result = generate_profile_embedding.run(profile.pk)

        profile.refresh_from_db()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "invalid_vector")
        self.assertEqual(profile.embedding, None)
        self.assertEqual(profile.embedding_content_hash, "")

    def test_missing_profile_is_handled(self):
        result = generate_profile_embedding.run(999999)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "missing_profile")


class ProfileEmbeddingTriggerTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="profile_trigger",
            email="profile_trigger@example.com",
            password="x",
        )
        self.profile = self.user.profil

    def test_semantic_profile_update_enqueues_embedding_refresh(self):
        serializer = ProfilUpdateSerializer(
            self.profile,
            data={"niveau_experience": "JUNIOR"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch("users.serializers.enqueue_profile_embedding_refresh") as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                serializer.save()

        mocked.assert_called_once_with(self.profile.pk)

    def test_non_semantic_profile_update_does_not_enqueue_embedding_refresh(self):
        serializer = ProfilUpdateSerializer(
            self.profile,
            data={"nom": "Updated"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch("users.serializers.enqueue_profile_embedding_refresh") as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                serializer.save()

        mocked.assert_not_called()

    def test_opportunity_type_filter_update_does_not_enqueue_embedding_refresh(self):
        serializer = ProfilUpdateSerializer(
            self.profile,
            data={"opportunity_types": ["JOB"]},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch("users.serializers.enqueue_profile_embedding_refresh") as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                serializer.save()

        mocked.assert_not_called()
