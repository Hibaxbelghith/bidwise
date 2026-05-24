from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from ai.esco_skill_embeddings import (
    ESCOSkillEmbeddingValidationError,
    embedding_model_matches,
    validate_embedding_shape,
    vector_dimension_matches,
)
from ai.esco_skill_index import (
    build_esco_skill_embedding_text,
    clear_esco_skill_index_cache,
    find_esco_skill_by_label,
    get_esco_skill_by_uri,
    get_esco_skill_index,
)
from ai.models import ESCOSkill


def _vector(value):
    return [float(value + index) for index in range(384)]


class ESCOSkillEmbeddingCommandTests(TestCase):
    def tearDown(self):
        clear_esco_skill_index_cache()

    @staticmethod
    def _fake_batch_encoder(texts, model_name=None, batch_size=None):
        return [[float(row_index + dim) for dim in range(384)] for row_index, _ in enumerate(texts, start=1)]

    @patch("ai.management.commands.generate_esco_skill_embeddings.service.generate_embeddings_batch")
    def test_generate_esco_skill_embeddings_persists_vectors(self, mock_generate_batch):
        mock_generate_batch.side_effect = self._fake_batch_encoder
        ESCOSkill.objects.bulk_create(
            [
                ESCOSkill(
                    uri="esco:skill_python",
                    preferred_label="Python",
                    alt_labels=["python programming"],
                ),
                ESCOSkill(
                    uri="esco:skill_react",
                    preferred_label="React",
                    alt_labels=["React.js"],
                ),
            ]
        )

        out = StringIO()
        call_command(
            "generate_esco_skill_embeddings",
            model="sentence-transformers/all-MiniLM-L6-v2",
            model_version="v1-test",
            batch_size=2,
            stdout=out,
        )

        rows = list(ESCOSkill.objects.order_by("uri"))
        self.assertTrue(all(row.embedding is not None for row in rows))
        self.assertTrue(all(len(row.embedding) == 384 for row in rows))
        self.assertTrue(all(row.embedding_model == "sentence-transformers/all-MiniLM-L6-v2" for row in rows))
        self.assertTrue(all(row.embedding_version == "v1-test" for row in rows))
        self.assertTrue(all(row.embedding_dimensions == 384 for row in rows))
        self.assertTrue(all(row.embedding_updated_at is not None for row in rows))
        self.assertIn("Updated: 2", out.getvalue())

    @patch("ai.management.commands.generate_esco_skill_embeddings.service.generate_embeddings_batch")
    def test_generate_esco_skill_embeddings_skips_existing_vectors_without_force(self, mock_generate_batch):
        mock_generate_batch.side_effect = self._fake_batch_encoder
        ESCOSkill.objects.create(
            uri="esco:skill_python",
            preferred_label="Python",
            alt_labels=["python programming"],
            embedding=_vector(1),
            embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            embedding_dimensions=384,
            embedding_version="prod-v1-fr",
            embedding_updated_at=timezone.now(),
        )

        out = StringIO()
        call_command("generate_esco_skill_embeddings", stdout=out)

        self.assertIn("No ESCO skills to process.", out.getvalue())
        mock_generate_batch.assert_not_called()

    @patch("ai.management.commands.generate_esco_skill_embeddings.service.generate_embeddings_batch")
    def test_generate_esco_skill_embeddings_blocks_dimension_mismatch(self, mock_generate_batch):
        mock_generate_batch.return_value = [[1.0, 2.0]]
        ESCOSkill.objects.create(
            uri="esco:skill_python",
            preferred_label="Python",
            alt_labels=["python programming"],
        )

        with self.assertRaisesMessage(
            CommandError,
            "Invalid embedding generated for ESCOSkill(uri=esco:skill_python)",
        ):
            call_command("generate_esco_skill_embeddings", stdout=StringIO())

        row = ESCOSkill.objects.get(uri="esco:skill_python")
        self.assertIsNone(row.embedding)
        self.assertEqual(row.embedding_model, "")
        self.assertIsNone(row.embedding_dimensions)
        self.assertEqual(row.embedding_version, "")
        self.assertIsNone(row.embedding_updated_at)

    @patch("ai.management.commands.generate_esco_skill_embeddings.service.generate_embeddings_batch")
    def test_generate_esco_skill_embeddings_requires_force_for_model_switch(self, mock_generate_batch):
        mock_generate_batch.side_effect = self._fake_batch_encoder
        ESCOSkill.objects.create(
            uri="esco:skill_python",
            preferred_label="Python",
            alt_labels=["python programming"],
            embedding=_vector(1),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dimensions=384,
            embedding_version="v1",
            embedding_updated_at=timezone.now(),
        )

        with self.assertRaisesMessage(
            CommandError,
            "Refusing to overwrite existing ESCO skill embeddings with different metadata",
        ):
            call_command(
                "generate_esco_skill_embeddings",
                model="BAAI/bge-small-en-v1.5",
                model_version="v1",
                stdout=StringIO(),
            )

        mock_generate_batch.assert_not_called()


class ESCOSkillIndexTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    def test_embedding_text_builder_includes_aliases(self):
        self.assertEqual(
            build_esco_skill_embedding_text("Python", ["python programming", "Py"]),
            "Python\naliases: python programming, Py",
        )

    def test_cached_lookup_is_case_insensitive_and_avoids_repeated_queries(self):
        ESCOSkill.objects.create(
            uri="esco:skill_react",
            preferred_label="React",
            alt_labels=["React.js", "ReactJS"],
            embedding=_vector(2),
            embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            embedding_dimensions=384,
            embedding_version="v1",
            embedding_updated_at=timezone.now(),
        )

        with CaptureQueriesContext(connection) as first_lookup:
            skill = find_esco_skill_by_label("react.js")

        self.assertEqual(skill.uri, "esco:skill_react")
        self.assertEqual(skill.preferred_label, "React")
        self.assertEqual(skill.embedding[0], 2.0)
        self.assertEqual(len(first_lookup), 1)

        with CaptureQueriesContext(connection) as second_lookup:
            skill = find_esco_skill_by_label("REACTJS")

        self.assertEqual(skill.uri, "esco:skill_react")
        self.assertEqual(len(second_lookup), 0)

        index = get_esco_skill_index()
        self.assertEqual(index.total_skills, 1)
        self.assertEqual(index.embedded_skill_count, 1)
        self.assertEqual(get_esco_skill_by_uri("esco:skill_react").preferred_label, "React")

    def test_empty_dataset_is_safe(self):
        index = get_esco_skill_index()

        self.assertTrue(index.is_empty)
        self.assertEqual(index.total_skills, 0)
        self.assertEqual(index.embedded_skill_count, 0)
        self.assertIsNone(find_esco_skill_by_label("python"))


class ESCOSkillValidationHelperTests(TestCase):
    def test_validate_embedding_shape_accepts_expected_dimension(self):
        self.assertEqual(len(validate_embedding_shape(_vector(1), expected_dimensions=384)), 384)

    def test_validate_embedding_shape_rejects_dimension_mismatch(self):
        with self.assertRaises(ESCOSkillEmbeddingValidationError):
            validate_embedding_shape([1.0, 2.0], expected_dimensions=384)

    def test_vector_dimension_matches_is_boolean_safe(self):
        self.assertTrue(vector_dimension_matches(_vector(3), expected_dimensions=384))
        self.assertFalse(vector_dimension_matches([1.0, 2.0], expected_dimensions=384))

    def test_embedding_model_matches_requires_model_version_and_dimensions(self):
        skill = ESCOSkill(
            uri="esco:skill_python",
            preferred_label="Python",
            embedding=_vector(1),
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_dimensions=384,
            embedding_version="v2-test",
            embedding_updated_at=timezone.now(),
        )

        self.assertTrue(
            embedding_model_matches(
                skill,
                "sentence-transformers/all-MiniLM-L6-v2",
                model_version="v2-test",
                expected_dimensions=384,
            )
        )
        self.assertFalse(
            embedding_model_matches(
                skill,
                "BAAI/bge-small-en-v1.5",
                model_version="v2-test",
                expected_dimensions=384,
            )
        )
