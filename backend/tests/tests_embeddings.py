from datetime import date
from io import StringIO
import math
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from opportunities.embeddings import service
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


class _FakeVector(list):
    def tolist(self):
        return list(self)


class _FakeSentenceTransformer:
    def __init__(self, model_name):
        self.model_name = model_name

    def encode(self, texts, **kwargs):
        outputs = []
        model_seed = (sum(ord(ch) for ch in self.model_name) % 17) + 1
        for text in texts:
            text_seed = (sum(ord(ch) for ch in text) % 31) + 1
            vector = _FakeVector(
                [((model_seed * 3) + text_seed + idx) / 100.0 for idx in range(128)]
            )
            outputs.append(vector)
        return outputs


class EmbeddingServiceTests(SimpleTestCase):
    def setUp(self):
        service.clear_model_cache()

    def tearDown(self):
        service.clear_model_cache()

    @patch("opportunities.embeddings.service._load_sentence_transformer")
    def test_embedding_generation_supports_multiple_models(self, mock_loader):
        mock_loader.side_effect = lambda model_name: _FakeSentenceTransformer(model_name)

        for model_name in service.EMBEDDING_MODELS:
            vector = service.generate_embedding("data engineer python", model_name=model_name)
            self.assertTrue(vector)
            self.assertGreater(len(vector), 100)

    @patch("opportunities.embeddings.service._load_sentence_transformer")
    def test_model_loaded_once_per_model_name(self, mock_loader):
        mock_loader.side_effect = lambda model_name: _FakeSentenceTransformer(model_name)
        model_name = "sentence-transformers/all-MiniLM-L6-v2"

        service.generate_embedding("text one", model_name=model_name)
        service.generate_embedding("text two", model_name=model_name)

        self.assertEqual(mock_loader.call_count, 1)

    @patch("opportunities.embeddings.service._load_sentence_transformer")
    def test_embeddings_differ_between_models(self, mock_loader):
        mock_loader.side_effect = lambda model_name: _FakeSentenceTransformer(model_name)

        text = "business analyst senior sousse cdi"
        vector_a = service.generate_embedding(
            text, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        vector_b = service.generate_embedding(text, model_name="BAAI/bge-small-en-v1.5")

        self.assertNotEqual(vector_a, vector_b)

    @patch("opportunities.embeddings.service._load_sentence_transformer")
    def test_generated_embedding_vector_is_l2_normalized(self, mock_loader):
        mock_loader.side_effect = lambda model_name: _FakeSentenceTransformer(model_name)

        vector = service.generate_embedding(
            "data engineer python sql aws",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        )
        norm = math.sqrt(sum(item * item for item in vector))
        self.assertAlmostEqual(norm, 1.0, places=6)


class GenerateEmbeddingsCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.source = SourceOpportunite.objects.create(
            nom="Test Source",
            url="https://example.com",
            type_source="AUTRE",
        )
        for index in range(3):
            Opportunite.objects.create(
                titre=f"Opportunity {index}",
                description=f"Business analyst role {index}",
                type_opportunite=TypeOpportunite.EMPLOI,
                statut=StatutOpportunite.ACTIVE,
                date_publication=date.today(),
                source=cls.source,
            )

    @staticmethod
    def _mock_batch_encoder(texts, model_name=None, batch_size=None):
        model_offset = 1 if model_name == "sentence-transformers/all-MiniLM-L6-v2" else 5
        vectors = []
        for row_index, _ in enumerate(texts):
            vectors.append([float(model_offset + row_index + dim) for dim in range(128)])
        return vectors

    @patch("opportunities.management.commands.generate_embeddings.service.generate_embeddings_batch")
    def test_generate_embeddings_and_model_switching(self, mock_generate_batch):
        mock_generate_batch.side_effect = self._mock_batch_encoder

        first_model = "sentence-transformers/all-MiniLM-L6-v2"
        second_model = "BAAI/bge-small-en-v1.5"
        first_model_identifier = f"{first_model}@v1-test"
        second_model_identifier = f"{second_model}@v2-test"

        call_command(
            "generate_embeddings",
            model=first_model,
            model_version="v1-test",
            batch_size=2,
        )
        rows = list(Opportunite.objects.order_by("id"))
        self.assertTrue(all(row.embedding_vector for row in rows))
        self.assertTrue(all(len(row.embedding_vector) > 100 for row in rows))
        self.assertTrue(all(row.embedding_model == first_model_identifier for row in rows))

        first_vectors = [row.embedding_vector[:] for row in rows]

        call_command(
            "generate_embeddings",
            model=second_model,
            model_version="v2-test",
            batch_size=2,
        )
        rows_after_skip = list(Opportunite.objects.order_by("id"))
        self.assertTrue(all(row.embedding_model == first_model_identifier for row in rows_after_skip))
        self.assertEqual(first_vectors, [row.embedding_vector for row in rows_after_skip])

        call_command(
            "generate_embeddings",
            model=second_model,
            model_version="v2-test",
            batch_size=2,
            force=True,
        )
        rows_after_force = list(Opportunite.objects.order_by("id"))
        self.assertTrue(all(row.embedding_model == second_model_identifier for row in rows_after_force))
        self.assertNotEqual(first_vectors, [row.embedding_vector for row in rows_after_force])

    @patch("opportunities.management.commands.benchmark_embeddings.service.generate_embeddings_batch")
    def test_benchmark_command_runs_with_multiple_models(self, mock_generate_batch):
        def fake_batch(texts, model_name=None, batch_size=None):
            model_offset = 1 if model_name == "sentence-transformers/all-MiniLM-L6-v2" else 7
            return [[float(model_offset + idx + dim) for dim in range(128)] for idx, _ in enumerate(texts)]

        mock_generate_batch.side_effect = fake_batch

        call_command(
            "benchmark_embeddings",
            models="sentence-transformers/all-MiniLM-L6-v2,BAAI/bge-small-en-v1.5",
            sample_size=3,
            top_k=1,
            batch_size=2,
        )

    def test_embedding_status_command_reports_configured_model_and_coverage(self):
        rows = list(Opportunite.objects.order_by("id"))
        rows[0].embedding_vector = [0.1, 0.2, 0.3]
        rows[0].embedding_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr"
        rows[0].save(update_fields=["embedding_vector", "embedding_model"])
        rows[1].embedding_vector = [0.5, 0.4, 0.3]
        rows[1].embedding_model = "BAAI/bge-small-en-v1.5@bench-v1"
        rows[1].save(update_fields=["embedding_vector", "embedding_model"])

        out = StringIO()
        call_command("embedding_status", stdout=out)
        rendered = out.getvalue()

        self.assertIn("Embeddings Status", rendered)
        self.assertIn(
            "Configured production model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr",
            rendered,
        )
        self.assertIn("Coverage: 2 (66.67%)", rendered)
