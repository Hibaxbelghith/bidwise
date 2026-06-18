from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ai.views import _rank_jobbert_recommendation_queryset


class FakeRecommendationQuerySet:
    def __init__(self, items):
        self.items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def exclude(self, *args, **kwargs):
        return self

    def only(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def __getitem__(self, value):
        return self.items[value]


class JobBertFallbackRecommendationTests(SimpleTestCase):
    def _call_fallback(self, *, profile_state):
        opportunity = SimpleNamespace(id=42, jobbert_embedding_vector=[0.8, 0.2])
        queryset = FakeRecommendationQuerySet([opportunity])
        profile = SimpleNamespace(id=7)
        ranked = [SimpleNamespace(id=42, match_score=0.73)]

        with (
            patch("ai.views.jobbert_enabled", return_value=True),
            patch("ai.views.get_or_build_profile_jobbert_embedding", return_value=[0.8, 0.2]),
            patch("ai.views.jobbert_model_name", return_value="fake-jobbert"),
            patch("ai.views.build_precomputed_jobbert_scores", return_value={42: 0.91}),
            patch("ai.views.rerank_ranked_opportunities", side_effect=lambda rows, features=None: rows),
            patch("ai.views.rank_opportunities", return_value=ranked) as rank_mock,
        ):
            result = _rank_jobbert_recommendation_queryset(
                profile=profile,
                queryset=queryset,
                features={"skills": ["Python"]},
                feedback={},
                profile_state=profile_state,
                limit=5,
            )

        self.assertEqual(result, ranked)
        return rank_mock.call_args.kwargs["mode"]

    def test_jobbert_fallback_uses_tolerant_mode_for_complete_profile(self):
        self.assertEqual(self._call_fallback(profile_state="complete"), "partial")

    def test_jobbert_fallback_preserves_partial_profile_mode(self):
        self.assertEqual(self._call_fallback(profile_state="partial"), "partial")
