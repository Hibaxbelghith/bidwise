from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from ai.recommendation_service import rank_opportunities


def _vector_with_similarity(similarity):
    return [float(similarity), max(0.0, 1.0 - float(similarity) ** 2) ** 0.5]


class RecommendationExperienceGapPenaltyTests(SimpleTestCase):
    def test_junior_profile_gets_no_penalty_for_junior_job(self):
        features = {
            "skills": ["Python"],
            "experience_years": 1,
            "experience_level": "JUNIOR",
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Junior Python Developer",
            skills=["Python"],
            experience_min=0,
            experience_max=2,
            embedding_vector=_vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertFalse(ranked.recommendation_debug["experience_gap_detected"])
        self.assertEqual(ranked.recommendation_debug["experience_gap_penalty"], 0.0)

    def test_junior_profile_gets_small_penalty_for_mid_level_job(self):
        features = {
            "skills": ["Python"],
            "experience_years": 1,
            "experience_level": "JUNIOR",
        }
        baseline = SimpleNamespace(
            id=1,
            titre="Backend Developer",
            skills=["Python"],
            experience_min=0,
            experience_max=2,
            embedding_vector=_vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )
        mid_level = SimpleNamespace(
            id=2,
            titre="Backend Developer",
            skills=["Python"],
            experience_min=2,
            experience_max=3,
            embedding_vector=_vector_with_similarity(0.60),
            date_publication=date(2026, 1, 1),
        )

        baseline_ranked = rank_opportunities([1.0, 0.0], [baseline], features=features)[0]
        penalized_ranked = rank_opportunities([1.0, 0.0], [mid_level], features=features)[0]

        self.assertEqual(penalized_ranked.recommendation_debug["experience_gap_penalty"], 0.02)
        self.assertLess(penalized_ranked.match_score, baseline_ranked.match_score)

    def test_senior_profile_gets_no_penalty_for_senior_job(self):
        features = {
            "skills": ["Python"],
            "experience_years": 7,
            "experience_level": "SENIOR",
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Senior Backend Architect",
            skills=["Python"],
            experience_min=5,
            experience_max=10,
            embedding_vector=_vector_with_similarity(0.70),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertFalse(ranked.recommendation_debug["experience_gap_detected"])
        self.assertEqual(ranked.recommendation_debug["experience_gap_penalty"], 0.0)

    def test_junior_profile_gets_stronger_penalty_for_senior_backend_role(self):
        features = {
            "skills": ["Python"],
            "roles": ["Backend Developer"],
            "experience_years": 1,
            "experience_level": "JUNIOR",
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Senior Backend Architect",
            skills=["Python"],
            experience_min=5,
            experience_max=10,
            embedding_vector=_vector_with_similarity(0.68),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertTrue(ranked.recommendation_debug["experience_gap_detected"])
        self.assertEqual(ranked.recommendation_debug["experience_gap_penalty"], 0.08)
        self.assertEqual(
            ranked.recommendation_debug["parsed_experience_range"]["effective_min_years"],
            6.0,
        )
        self.assertEqual(
            ranked.recommendation_debug["parsed_experience_range"]["title_seniority_keyword"],
            "architect",
        )

    def test_internship_profile_gets_stronger_penalty_for_senior_architect_role(self):
        features = {
            "skills": ["React"],
            "employment_types": ["INTERNSHIP"],
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Senior Frontend Architect",
            skills=["React"],
            embedding_vector=_vector_with_similarity(0.72),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities([1.0, 0.0], [opportunity], features=features)[0]

        self.assertTrue(ranked.recommendation_debug["experience_gap_detected"])
        self.assertEqual(ranked.recommendation_debug["experience_gap_penalty"], 0.1)
        self.assertEqual(
            ranked.recommendation_debug["parsed_experience_range"]["profile_source"],
            "internship_preference",
        )

    def test_partial_mode_scales_penalty_and_preserves_sparse_match(self):
        features = {
            "skills": ["Python"],
            "experience_years": 1,
            "experience_level": "JUNIOR",
        }
        opportunity = SimpleNamespace(
            id=1,
            titre="Senior Backend Architect",
            skills=["Python"],
            experience_min=5,
            experience_max=10,
            application_count=2,
            embedding_vector=_vector_with_similarity(0.82),
            date_publication=date(2026, 1, 1),
        )

        ranked = rank_opportunities(
            [1.0, 0.0],
            [opportunity],
            features=features,
            mode="partial",
            min_score=0.1,
        )[0]

        self.assertGreater(ranked.match_score, 0.1)
        self.assertEqual(ranked.recommendation_debug["experience_gap_penalty"], 0.0408)
        self.assertEqual(ranked.recommendation_debug["fallback_override_if_any"], "partial_mode_scaled,strong_semantic_scaled")
