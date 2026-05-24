from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from ai.recommendation_llm import (
    apply_llm_hierarchy_validation_to_ranked,
    should_validate_llm_hierarchy,
)


class RecommendationLLMTests(SimpleTestCase):
    def test_should_validate_only_needs_llm_strong_or_high_score(self):
        low_review = SimpleNamespace(
            match_score=0.42,
            recommendation_debug={"hierarchy_validation": {"needs_llm": True}},
        )
        high_review = SimpleNamespace(
            match_score=0.61,
            recommendation_debug={"hierarchy_validation": {"needs_llm": True}},
        )
        strong_low_score = SimpleNamespace(
            match_score=0.45,
            recommendation_debug={"hierarchy_validation": {"needs_llm": True}},
        )

        self.assertFalse(should_validate_llm_hierarchy(low_review, "RELATED_REVIEW"))
        self.assertTrue(should_validate_llm_hierarchy(high_review, "RELATED_REVIEW"))
        self.assertTrue(should_validate_llm_hierarchy(strong_low_score, "STRONG_MATCH"))

    @override_settings(RECOMMENDATION_LLM_HIERARCHY_ENABLED=False)
    def test_disabled_flag_skips_llm_validation(self):
        opportunity = SimpleNamespace(
            match_score=0.9,
            recommendation_debug={"hierarchy_validation": {"needs_llm": True}},
        )

        with patch("ai.recommendation_llm._validate_hierarchy_with_cache") as validate:
            stats = apply_llm_hierarchy_validation_to_ranked(
                [opportunity],
                features={},
                profile_text="Role: IT Helpdesk.",
            )

        self.assertEqual(stats, {"eligible": 0, "validated": 0, "errors": 0})
        validate.assert_not_called()
