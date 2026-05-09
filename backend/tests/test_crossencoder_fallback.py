from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.crossencoder.models import CrossEncoderTimeout, CrossEncoderUnavailable
from ai.crossencoder.service import blend_scores, rerank_ranked_opportunities


def opportunity(identifier, title, score):
    return SimpleNamespace(
        id=identifier,
        titre=title,
        description=title,
        skills=[],
        date_publication=date(2026, 5, 1),
        match_score=score,
        score=score,
        similarity_score=score,
        semantic_score=score,
        business_score=0.0,
        feedback_score=0.0,
        score_label="Good match",
        score_level="MEDIUM",
        reason=[],
    )


class CrossEncoderFallbackTests(SimpleTestCase):
    def test_disabled_crossencoder_preserves_existing_ranking(self):
        rows = [
            opportunity(1, "Python Backend Developer", 0.80),
            opportunity(2, "Accounting Assistant", 0.70),
        ]

        with override_settings(CROSS_ENCODER_ENABLED=False):
            with patch("ai.crossencoder.service.score_opportunities") as mocked:
                ranked = rerank_ranked_opportunities(rows, features={"skills": ["Python"]})

        self.assertEqual([item.id for item in ranked], [1, 2])
        self.assertFalse(mocked.called)

    @override_settings(CROSS_ENCODER_ENABLED=True)
    def test_model_unavailable_fallback_preserves_existing_ranking(self):
        rows = [
            opportunity(1, "Python Backend Developer", 0.80),
            opportunity(2, "Accounting Assistant", 0.70),
        ]

        with patch(
            "ai.crossencoder.service.score_opportunities",
            side_effect=CrossEncoderUnavailable("model missing"),
        ):
            ranked = rerank_ranked_opportunities(rows, features={"skills": ["Python"]})

        self.assertEqual([item.id for item in ranked], [1, 2])
        self.assertEqual(rows[0].match_score, 0.80)

    @override_settings(CROSS_ENCODER_ENABLED=True)
    def test_timeout_fallback_preserves_existing_ranking(self):
        rows = [
            opportunity(1, "Frontend React Developer", 0.82),
            opportunity(2, "Recruiter", 0.75),
        ]

        with patch(
            "ai.crossencoder.service.score_opportunities",
            side_effect=CrossEncoderTimeout("timeout"),
        ):
            ranked = rerank_ranked_opportunities(rows, features={"skills": ["React"]})

        self.assertEqual([item.id for item in ranked], [1, 2])

    @override_settings(CROSS_ENCODER_ENABLED=True)
    def test_empty_profile_signal_skips_crossencoder(self):
        rows = [opportunity(1, "Recent Job", 0.50)]

        with patch("ai.crossencoder.service.score_opportunities") as mocked:
            ranked = rerank_ranked_opportunities(rows, features={})

        self.assertEqual([item.id for item in ranked], [1])
        self.assertFalse(mocked.called)

    def test_blending_keeps_existing_score_weighted(self):
        self.assertAlmostEqual(blend_scores(0.80, 0.40, 0.25), 0.70)
        self.assertAlmostEqual(blend_scores(0.80, 1.00, 0.25), 0.85)
