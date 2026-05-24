from types import SimpleNamespace

from django.test import SimpleTestCase

from ai.hierarchy_llm import LLMHierarchyValidation
from ai.management.commands.benchmark_final_recommendation_profiles import (
    _apply_llm_hierarchy_result,
    _compact_row,
    _should_validate_llm_hierarchy,
)


class BenchmarkLLMHierarchyValidationTests(SimpleTestCase):
    def test_compatible_llm_result_clears_needs_llm_for_benchmark_row(self):
        opportunity = SimpleNamespace(
            recommendation_debug={
                "hierarchy_validation": {
                    "needs_llm": True,
                    "hierarchy_issue": "none",
                    "score_multiplier": 1.0,
                    "reason": "Ambiguous hierarchy gap; LLM validation recommended",
                }
            }
        )

        _apply_llm_hierarchy_result(
            opportunity,
            LLMHierarchyValidation(
                is_compatible=True,
                confidence=0.86,
                issue="none",
                reason="Le niveau est compatible.",
                provider="fake",
                model="fake-model",
                cache_key="abc",
            ),
        )

        validation = opportunity.recommendation_debug["hierarchy_validation"]
        self.assertFalse(validation["needs_llm"])
        self.assertEqual(validation["hierarchy_issue"], "none")
        self.assertEqual(validation["score_multiplier"], 1.0)
        self.assertEqual(opportunity.recommendation_debug["llm_hierarchy_validation"]["provider"], "fake")

    def test_incompatible_llm_result_marks_reviewable_hierarchy_issue(self):
        opportunity = SimpleNamespace(
            recommendation_debug={
                "hierarchy_validation": {
                    "needs_llm": True,
                    "hierarchy_issue": "none",
                    "score_multiplier": 1.0,
                    "reason": "Slight hierarchy gap; keep as reviewable",
                    "opportunity_signal": {
                        "responsibility_terms": ["responsable"],
                    },
                }
            }
        )

        _apply_llm_hierarchy_result(
            opportunity,
            LLMHierarchyValidation(
                is_compatible=False,
                confidence=0.9,
                issue="responsibility_gap",
                reason="Le poste demande un responsable, pas un contributeur.",
            ),
        )

        validation = opportunity.recommendation_debug["hierarchy_validation"]
        self.assertFalse(validation["needs_llm"])
        self.assertEqual(validation["hierarchy_issue"], "responsibility_gap")
        self.assertLess(validation["score_multiplier"], 0.7)
        self.assertEqual(validation["reason"], "Le poste demande un responsable, pas un contributeur.")

    def test_low_confidence_llm_result_keeps_needs_llm(self):
        opportunity = SimpleNamespace(
            recommendation_debug={
                "hierarchy_validation": {
                    "needs_llm": True,
                    "hierarchy_issue": "none",
                    "score_multiplier": 1.0,
                }
            }
        )

        _apply_llm_hierarchy_result(
            opportunity,
            LLMHierarchyValidation(
                is_compatible=True,
                confidence=0.4,
                issue="none",
                reason="Information insuffisante.",
            ),
        )

        validation = opportunity.recommendation_debug["hierarchy_validation"]
        self.assertTrue(validation["needs_llm"])
        self.assertEqual(validation["hierarchy_issue"], "none")

    def test_incompatible_llm_result_without_explicit_terms_keeps_needs_llm(self):
        opportunity = SimpleNamespace(
            recommendation_debug={
                "hierarchy_validation": {
                    "needs_llm": True,
                    "hierarchy_issue": "none",
                    "score_multiplier": 1.0,
                    "opportunity_signal": {
                        "seniority": 2,
                        "qualification": 2,
                        "responsibility": 2,
                        "seniority_terms": [],
                        "qualification_terms": [],
                        "responsibility_terms": [],
                    },
                }
            }
        )

        _apply_llm_hierarchy_result(
            opportunity,
            LLMHierarchyValidation(
                is_compatible=False,
                confidence=0.8,
                issue="seniority_gap",
                reason="Le profil candidat est junior et l'offre demande un niveau superieur.",
            ),
        )

        validation = opportunity.recommendation_debug["hierarchy_validation"]
        self.assertTrue(validation["needs_llm"])
        self.assertEqual(validation["hierarchy_issue"], "none")

    def test_exact_role_and_skill_match_survives_llm_seniority_concern(self):
        opportunity = SimpleNamespace(
            titre="IT Helpdesk Officer",
            match_score=0.857,
            semantic_score=0.696,
            skills=["support helpdesk", "Windows", "Microsoft 365"],
            description="Support users on Windows and Microsoft 365.",
            recommendation_debug={
                "hierarchy_validation": {
                    "needs_llm": True,
                    "hierarchy_issue": "none",
                    "score_multiplier": 1.0,
                    "opportunity_signal": {
                        "seniority_terms": ["confirme"],
                    },
                }
            },
        )

        _apply_llm_hierarchy_result(
            opportunity,
            LLMHierarchyValidation(
                is_compatible=False,
                confidence=0.8,
                issue="seniority_gap",
                reason="Le profil candidat est junior.",
            ),
            features={
                "target_roles": ["IT Helpdesk Officer"],
                "skills": ["support helpdesk", "Windows", "Microsoft 365"],
            },
        )

        validation = opportunity.recommendation_debug["hierarchy_validation"]
        self.assertFalse(validation["needs_llm"])
        self.assertEqual(validation["hierarchy_issue"], "none")
        self.assertEqual(
            validation["reason"],
            "Exact role and skill evidence override weak LLM hierarchy concern",
        )
        policy = opportunity.recommendation_debug["llm_hierarchy_policy"]
        self.assertFalse(policy["applied"])
        self.assertTrue(policy["overridden_by_exact_evidence"])

    def test_compact_row_exposes_llm_override_policy(self):
        opportunity = SimpleNamespace(
            pk=3427,
            titre="IT Helpdesk Officer",
            organisation_nom="IBN AL BAYTAR HIKMA",
            ville="Ariana",
            source=SimpleNamespace(nom="Keejob"),
            match_score=0.857,
            reason=["support helpdesk"],
            recommendation_debug={
                "jobbert_score": 0.696,
                "hierarchy_validation": {
                    "needs_llm": False,
                    "hierarchy_issue": "none",
                },
                "llm_hierarchy_validation": {
                    "provider": "ollama",
                    "issue": "seniority_gap",
                },
                "llm_hierarchy_policy": {
                    "applied": False,
                    "overridden_by_exact_evidence": True,
                    "kept_for_review": False,
                    "reason": "Exact role and skill evidence override weak LLM hierarchy concern",
                },
            },
        )

        row = _compact_row(opportunity, "STRONG_MATCH", "Strong role, skill, and semantic evidence")

        self.assertTrue(row["llm_overridden_by_exact_evidence"])
        self.assertEqual(row["llm_hierarchy_policy"]["reason"], "Exact role and skill evidence override weak LLM hierarchy concern")

    def test_llm_validation_is_limited_to_strong_or_high_scoring_rows(self):
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

        self.assertFalse(_should_validate_llm_hierarchy(low_review, "RELATED_REVIEW"))
        self.assertTrue(_should_validate_llm_hierarchy(high_review, "RELATED_REVIEW"))
        self.assertTrue(_should_validate_llm_hierarchy(strong_low_score, "STRONG_MATCH"))
