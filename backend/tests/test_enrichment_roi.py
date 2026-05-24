from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase

from ai.enrichment_roi import RecommendationStats, score_opportunity_for_enrichment
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


class EnrichmentROITests(TestCase):
    def setUp(self):
        self.linkedin = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://linkedin.example",
            type_source="SITE_EMPLOI",
        )
        self.keejob = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://keejob.example",
            type_source="SITE_EMPLOI",
        )
        self.marches = SourceOpportunite.objects.create(
            nom="MarchesPublics",
            url="https://marches.example",
            type_source="PORTAIL_PROJET",
        )

    def _opportunity(self, **kwargs):
        defaults = {
            "titre": "Backend Django Developer",
            "description": "Build Django APIs with PostgreSQL and Redis. " * 20,
            "organisation_nom": "Tech",
            "ville": "Tunis",
            "contract_type": "CDI",
            "skills": [],
            "raw_skills": [],
            "normalized_skills": [],
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_limite": date.today() + timedelta(days=30),
            "source": self.linkedin,
            "extra_data": {},
        }
        defaults.update(kwargs)
        return Opportunite.objects.create(**defaults)

    def test_p1_prioritizes_rich_description_with_weak_skills(self):
        opportunity = self._opportunity(skills=["Python", "Django"])

        roi = score_opportunity_for_enrichment(opportunity)

        self.assertTrue(roi.eligible)
        self.assertEqual(roi.priority, "P1")
        self.assertIn("P1 rich description with weak skills", roi.reasons)
        self.assertEqual(roi.skill_count, 2)

    def test_low_coverage_source_with_short_but_usable_description_can_be_p3(self):
        opportunity = self._opportunity(
            description=(
                "Role: Backend Developer. Skills: Django, PostgreSQL, Redis. "
                "Build APIs and maintain backend services for business applications. "
                "Collaborate with product teams."
            ),
            skills=[],
            raw_skills=[],
        )

        roi = score_opportunity_for_enrichment(opportunity)

        self.assertTrue(roi.eligible)
        self.assertEqual(roi.priority, "P3")
        self.assertIn("P3 low coverage source: LinkedIn", roi.reasons)
        self.assertNotIn("P1 rich description with weak skills", roi.reasons)

    def test_dark_offer_gets_p2_boost(self):
        opportunity = self._opportunity(source=self.keejob, skills=["Python", "Django", "PostgreSQL"])

        roi = score_opportunity_for_enrichment(
            opportunity,
            recommendation_stats=RecommendationStats(appeared_count=3, strong_count=0, related_count=3),
        )

        self.assertTrue(roi.eligible)
        self.assertGreaterEqual(roi.score, 55)
        self.assertIn("P2 dark offer: appeared in recommendations without STRONG_MATCH", roi.reasons)

    def test_expiring_opportunity_is_excluded_even_when_high_roi(self):
        opportunity = self._opportunity(date_limite=date.today() + timedelta(days=2))

        roi = score_opportunity_for_enrichment(opportunity, exclude_expiring_days=7)

        self.assertFalse(roi.eligible)
        self.assertEqual(roi.priority, "P0")
        self.assertIn("deadline_too_close", roi.exclusions)

    def test_too_short_description_is_excluded(self):
        opportunity = self._opportunity(description="Backend Django.")

        roi = score_opportunity_for_enrichment(opportunity)

        self.assertFalse(roi.eligible)
        self.assertIn("short_description", roi.exclusions)

    def test_non_job_source_is_excluded(self):
        opportunity = self._opportunity(
            source=self.marches,
            type_opportunite=TypeOpportunite.PROJET,
            titre="Travaux de maintenance",
        )

        roi = score_opportunity_for_enrichment(opportunity)

        self.assertFalse(roi.eligible)
        self.assertIn("non_job_type", roi.exclusions)
        self.assertIn("non_job_source", roi.exclusions)

    def test_already_llm_enriched_is_not_selected(self):
        opportunity = self._opportunity(extra_data={"llm_enrichment": {"confidence": 0.9}})

        roi = score_opportunity_for_enrichment(opportunity)

        self.assertFalse(roi.eligible)
        self.assertEqual(roi.score, 0.0)
        self.assertIn("already_llm_enriched", roi.exclusions)
