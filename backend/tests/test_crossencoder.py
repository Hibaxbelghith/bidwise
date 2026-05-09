from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.crossencoder.loader import get_cross_encoder_model, reset_cross_encoder_cache
from ai.crossencoder.scoring import (
    _normalize_score,
    build_opportunity_text,
    build_profile_text,
    score_opportunities,
)


class CrossEncoderCoreTests(SimpleTestCase):
    def setUp(self):
        reset_cross_encoder_cache()

    def tearDown(self):
        reset_cross_encoder_cache()

    def test_loader_lazily_caches_singleton_cpu_model(self):
        class FakeCrossEncoder:
            loads = 0

            def __init__(self, model_name, **kwargs):
                FakeCrossEncoder.loads += 1
                self.model_name = model_name
                self.kwargs = kwargs

        fake_module = SimpleNamespace(CrossEncoder=FakeCrossEncoder)

        with override_settings(
            CROSS_ENCODER_ENABLED=True,
            CROSS_ENCODER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2",
            CROSS_ENCODER_LOCAL_FILES_ONLY=False,
        ):
            with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
                first = get_cross_encoder_model()
                second = get_cross_encoder_model()

        self.assertIs(first, second)
        self.assertEqual(FakeCrossEncoder.loads, 1)
        self.assertEqual(first.model_name, "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.assertEqual(first.kwargs["device"], "cpu")

    def test_pair_text_contains_profile_cv_and_job_fields(self):
        features = {
            "skills": ["Python", "Django"],
            "target_roles": ["Backend Developer"],
            "interests": ["SaaS"],
            "experience_level": "SENIOR",
            "experience_years": 6,
            "resume_text": "Built APIs with PostgreSQL and Redis.",
        }
        opportunity = SimpleNamespace(
            titre="Python Backend Engineer",
            description="Build Django APIs for a SaaS platform.",
            skills=["Python", "PostgreSQL"],
            organisation_nom="Acme",
            ville="Tunis",
        )

        profile_text = build_profile_text(features)
        opportunity_text = build_opportunity_text(opportunity)

        self.assertIn("PROFILE:", profile_text)
        self.assertIn("Semantic CV summary: Built APIs", profile_text)
        self.assertIn("Skills: Python, Django", profile_text)
        self.assertIn("JOB:", opportunity_text)
        self.assertIn("Title: Python Backend Engineer", opportunity_text)
        self.assertIn("Description: Build Django APIs", opportunity_text)

    def test_scores_are_normalized_and_return_metadata(self):
        class FakeModel:
            def predict(self, pairs, **kwargs):
                return [-2.0, 0.5, 2.0]

        opportunities = [
            SimpleNamespace(titre=f"Job {index}", description="Python role", skills=["Python"])
            for index in range(3)
        ]

        with override_settings(CROSS_ENCODER_ENABLED=True, CROSS_ENCODER_TIMEOUT_SECONDS=5.0):
            with patch("ai.crossencoder.scoring.get_cross_encoder_model", return_value=FakeModel()):
                scores = score_opportunities({"skills": ["Python"]}, opportunities)

        self.assertEqual(len(scores), 3)
        self.assertLess(scores[0].score, scores[1].score)
        self.assertLess(scores[1].score, scores[2].score)
        self.assertEqual(scores[0].metadata["pair_index"], 0)

    def test_normalize_score_accepts_probabilities_and_logits(self):
        self.assertEqual(_normalize_score(0.7), 0.7)
        self.assertGreater(_normalize_score(3.0), 0.9)
        self.assertLess(_normalize_score(-3.0), 0.1)
