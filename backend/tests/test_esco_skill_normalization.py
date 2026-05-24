import math
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from ai.esco_skill_index import clear_esco_skill_index_cache
from ai.esco_skill_normalization import normalize_skills_to_esco
from ai.models import ESCOSkill


DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_VERSION = "prod-v1-fr"
DEFAULT_DIMENSIONS = 384


def _unit_vector(index: int) -> list[float]:
    vector = [0.0] * DEFAULT_DIMENSIONS
    vector[index] = 1.0
    return vector


def _similarity_vector(index: int, similarity: float) -> list[float]:
    vector = [0.0] * DEFAULT_DIMENSIONS
    vector[index] = similarity
    adjacent = min(index + 1, DEFAULT_DIMENSIONS - 1)
    vector[adjacent] = math.sqrt(max(0.0, 1.0 - similarity ** 2))
    return vector


def _embedded_skill(
    *,
    uri: str,
    preferred_label: str,
    preferred_label_en: str = "",
    preferred_label_fr: str = "",
    alt_labels: list[str] | None = None,
    alt_labels_en: list[str] | None = None,
    alt_labels_fr: list[str] | None = None,
    hidden_labels_en: list[str] | None = None,
    hidden_labels_fr: list[str] | None = None,
    embedding: list[float] | None = None,
    embedding_model: str = DEFAULT_MODEL,
    embedding_version: str = DEFAULT_VERSION,
    embedding_dimensions: int = DEFAULT_DIMENSIONS,
) -> ESCOSkill:
    return ESCOSkill.objects.create(
        uri=uri,
        preferred_label=preferred_label,
        alt_labels=alt_labels or [],
        preferred_label_en=preferred_label_en,
        preferred_label_fr=preferred_label_fr,
        alt_labels_en=alt_labels_en or [],
        alt_labels_fr=alt_labels_fr or [],
        hidden_labels_en=hidden_labels_en or [],
        hidden_labels_fr=hidden_labels_fr or [],
        search_text_multilingual="",
        embedding=embedding,
        embedding_model=embedding_model if embedding is not None else "",
        embedding_dimensions=embedding_dimensions if embedding is not None else None,
        embedding_version=embedding_version if embedding is not None else "",
        embedding_updated_at=timezone.now() if embedding is not None else None,
    )


class ESCOSkillNormalizationTests(TestCase):
    def setUp(self):
        clear_esco_skill_index_cache()

    def tearDown(self):
        clear_esco_skill_index_cache()

    def test_normalize_skills_to_esco_exact_matches_cover_en_and_fr_aliases(self):
        _embedded_skill(
            uri="esco:skill_react",
            preferred_label="React",
            preferred_label_en="React",
            alt_labels=["React.js", "ReactJS"],
            alt_labels_en=["React.js", "ReactJS"],
        )
        _embedded_skill(
            uri="esco:skill_javascript",
            preferred_label="JavaScript",
            preferred_label_en="JavaScript",
            alt_labels=["JS"],
            alt_labels_en=["JS"],
        )
        _embedded_skill(
            uri="esco:skill_python",
            preferred_label="Python",
            preferred_label_en="Python",
            preferred_label_fr="Python (programmation informatique)",
            alt_labels=["Python3", "Py3K"],
            alt_labels_en=["Python3", "Py3K"],
            alt_labels_fr=["programmation python"],
            hidden_labels_en=["python prog"],
        )
        _embedded_skill(
            uri="esco:skill_seo",
            preferred_label="Search engine optimisation",
            preferred_label_en="Search engine optimisation",
            alt_labels=["SEO"],
            alt_labels_en=["SEO"],
        )
        _embedded_skill(
            uri="esco:skill_digital_marketing",
            preferred_label="Digital marketing",
            preferred_label_en="Digital marketing",
            preferred_label_fr="marketing numérique",
            alt_labels_fr=["Marketing Digital"],
        )

        results = normalize_skills_to_esco(
            [
                "ReactJS",
                "react.js",
                "JS",
                "Python3",
                "Py3K",
                "programmation python",
                "python prog",
                "SEO",
                "Marketing Digital",
                "\ufeff ReactJS \x00",
            ]
        )

        self.assertEqual(len(results), 9)
        by_raw = {item.raw_skill: item for item in results}
        self.assertEqual(by_raw["ReactJS"].esco_uri, "esco:skill_react")
        self.assertEqual(by_raw["ReactJS"].match_type, "alt_label")
        self.assertEqual(by_raw["react.js"].esco_uri, "esco:skill_react")
        self.assertEqual(by_raw["JS"].esco_uri, "esco:skill_javascript")
        self.assertEqual(by_raw["Python3"].esco_uri, "esco:skill_python")
        self.assertEqual(by_raw["Py3K"].esco_uri, "esco:skill_python")
        self.assertEqual(by_raw["programmation python"].esco_uri, "esco:skill_python")
        self.assertEqual(by_raw["python prog"].match_type, "hidden_label")
        self.assertEqual(by_raw["SEO"].esco_uri, "esco:skill_seo")
        self.assertNotEqual(by_raw["SEO"].esco_uri, "esco:skill_react")
        self.assertEqual(by_raw["Marketing Digital"].esco_uri, "esco:skill_digital_marketing")
        self.assertNotEqual(by_raw["Marketing Digital"].canonical_skill, "Machine learning")
        self.assertEqual(by_raw["ReactJS"].similarity, 1.0)

    @patch("ai.esco_skill_normalization.embedding_service.generate_embeddings_batch")
    def test_normalize_skills_to_esco_uses_semantic_fallback_after_exact_failures(self, mock_generate_batch):
        _embedded_skill(
            uri="esco:skill_tensorflow",
            preferred_label="TensorFlow",
            preferred_label_en="TensorFlow",
            embedding=_unit_vector(0),
        )
        _embedded_skill(
            uri="esco:skill_react",
            preferred_label="React",
            preferred_label_en="React",
            embedding=_unit_vector(1),
        )

        def _fake_batch_encoder(texts, model_name=None, batch_size=None):
            self.assertEqual(model_name, DEFAULT_MODEL)
            mapping = {
                "Tensor Flow": _unit_vector(0),
                "Webmaster": _unit_vector(1),
            }
            return [mapping[text] for text in texts]

        mock_generate_batch.side_effect = _fake_batch_encoder

        results = normalize_skills_to_esco(
            ["Tensor Flow", "Webmaster"],
            similarity_threshold=0.72,
            max_candidates=3,
        )

        self.assertEqual(results[0].esco_uri, "esco:skill_tensorflow")
        self.assertEqual(results[0].match_type, "semantic")
        self.assertGreaterEqual(results[0].similarity or 0.0, 0.99)
        self.assertEqual(results[0].embedding_model, DEFAULT_MODEL)
        self.assertEqual(results[1].match_type, "unmatched")
        self.assertIsNone(results[1].esco_uri)

    @patch("ai.esco_skill_normalization.embedding_service.generate_embeddings_batch")
    def test_normalize_skills_to_esco_respects_threshold(self, mock_generate_batch):
        _embedded_skill(
            uri="esco:skill_tensorflow",
            preferred_label="TensorFlow",
            preferred_label_en="TensorFlow",
            embedding=_unit_vector(0),
        )
        mock_generate_batch.return_value = [_similarity_vector(0, 0.71)]

        result = normalize_skills_to_esco(["Tensor Flow"], similarity_threshold=0.72)[0]

        self.assertEqual(result.match_type, "unmatched")
        self.assertIsNone(result.esco_uri)
        self.assertEqual(result.unmatched_reason, "semantic_below_threshold")

    def test_normalize_skills_to_esco_handles_empty_input_and_duplicates(self):
        _embedded_skill(
            uri="esco:skill_react",
            preferred_label="React",
            preferred_label_en="React",
            alt_labels=["ReactJS"],
            alt_labels_en=["ReactJS"],
        )

        self.assertEqual(normalize_skills_to_esco([]), [])
        results = normalize_skills_to_esco(["ReactJS", "reactjs", " ReactJS "])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].esco_uri, "esco:skill_react")

    def test_normalize_skills_to_esco_prefers_unique_official_exact_match_over_legacy_collision(self):
        _embedded_skill(
            uri="esco:skill_javascript",
            preferred_label="JavaScript",
            preferred_label_en="JavaScript",
        )
        _embedded_skill(
            uri="http://data.europa.eu/esco/skill/3cd569a2-4f88-4c1e-9995-8dce8c5e51a7",
            preferred_label="JavaScript",
            preferred_label_en="JavaScript",
        )

        result = normalize_skills_to_esco(["JavaScript"])[0]

        self.assertEqual(
            result.esco_uri,
            "http://data.europa.eu/esco/skill/3cd569a2-4f88-4c1e-9995-8dce8c5e51a7",
        )
        self.assertEqual(result.match_type, "preferred_label")

    def test_normalize_skills_to_esco_promotes_unique_official_alt_label_over_legacy_preferred(self):
        _embedded_skill(
            uri="esco:skill_python",
            preferred_label="Python",
            preferred_label_en="Python",
        )
        _embedded_skill(
            uri="http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d",
            preferred_label="Python (computer programming)",
            preferred_label_en="Python (computer programming)",
            alt_labels_en=["Python"],
        )

        result = normalize_skills_to_esco(["Python"])[0]

        self.assertEqual(
            result.esco_uri,
            "http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d",
        )
        self.assertEqual(result.match_type, "alt_label")

    @patch("ai.esco_skill_normalization.embedding_service.generate_embeddings_batch")
    def test_normalize_skills_to_esco_ignores_invalid_query_vectors(self, mock_generate_batch):
        _embedded_skill(
            uri="esco:skill_tensorflow",
            preferred_label="TensorFlow",
            preferred_label_en="TensorFlow",
            embedding=_unit_vector(0),
        )
        mock_generate_batch.return_value = [[1.0, 2.0]]

        result = normalize_skills_to_esco(["Tensor Flow"])[0]

        self.assertEqual(result.match_type, "unmatched")
        self.assertEqual(result.unmatched_reason, "invalid_query_vector")

    @patch(
        "ai.esco_skill_normalization.embedding_service.generate_embeddings_batch",
        side_effect=ValueError("Unsupported embedding model"),
    )
    def test_normalize_skills_to_esco_fails_softly_on_incompatible_embedding_metadata(self, mock_generate_batch):
        _embedded_skill(
            uri="esco:skill_tensorflow",
            preferred_label="TensorFlow",
            preferred_label_en="TensorFlow",
            embedding=_unit_vector(0),
            embedding_model="custom/unsupported-model",
            embedding_version="v-custom",
        )

        result = normalize_skills_to_esco(["Tensor Flow"])[0]

        self.assertEqual(result.match_type, "unmatched")
        self.assertEqual(result.unmatched_reason, "semantic_embedding_batch_invalid")
        mock_generate_batch.assert_called_once()
