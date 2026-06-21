from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from ai.tender_recommendation_service import (
    TenderPreferences,
    category_match,
    get_tender_opportunities,
    score_tender,
)
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


class TenderRecommendationTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.source = SourceOpportunite.objects.create(
            nom="MarchesPublics",
            url="https://www.marchespublics.gov.tn",
            type_source="PORTAIL_PROJET",
        )

    def create_tender(self, **overrides):
        values = {
            "titre": "Achat de mat\u00e9riels informatiques",
            "description": "Appel d'offres pour des \u00e9quipements informatiques et r\u00e9seau.",
            "organisation_nom": "Acheteur Public",
            "type_opportunite": TypeOpportunite.PROJET,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": self.today - timedelta(days=5),
            "date_limite": self.today + timedelta(days=10),
            "ville": "Tunis",
            "source": self.source,
            "extra_data": {"type_commande": "Biens/ Mat\u00e9riels informatiques"},
        }
        values.update(overrides)
        return Opportunite.objects.create(**values)

    def test_expired_tender_is_excluded_from_results(self):
        expired = self.create_tender(
            titre="Expired tender",
            date_limite=self.today - timedelta(days=1),
        )
        active = self.create_tender(
            titre="Active tender",
            date_limite=self.today + timedelta(days=3),
        )

        results = get_tender_opportunities(queryset=Opportunite.objects.all(), limit=10)
        result_ids = [item["opportunity"].id for item in results]

        self.assertIn(active.id, result_ids)
        self.assertNotIn(expired.id, result_ids)

    def test_incomplete_or_visitor_profile_returns_general_watch_sorted_by_deadline(self):
        later = self.create_tender(
            titre="Later deadline",
            date_limite=self.today + timedelta(days=12),
        )
        sooner = self.create_tender(
            titre="Sooner deadline",
            date_limite=self.today + timedelta(days=2),
        )

        results = get_tender_opportunities(user=None, queryset=Opportunite.objects.all(), limit=10)

        self.assertEqual([item["opportunity"].id for item in results], [sooner.id, later.id])
        self.assertEqual(results[0]["priority"], "Veille g\u00e9n\u00e9rale")
        self.assertIsNone(results[0]["score"])

    def test_exact_subcategory_returns_full_category_match(self):
        self.assertEqual(
            category_match(
                ["Biens"],
                ["Mat\u00e9riels informatiques"],
                "Biens/ Mat\u00e9riels informatiques",
            ),
            1.0,
        )

    def test_main_category_only_returns_partial_category_match(self):
        self.assertEqual(
            category_match(
                ["Biens"],
                ["Mat\u00e9riel M\u00e9dical"],
                "Biens/ Mat\u00e9riels informatiques",
            ),
            0.35,
        )

    def test_region_execution_takes_priority_over_display_city(self):
        tender = self.create_tender(
            ville="Tunis",
            extra_data={
                "type_commande": "Biens/ Mat\u00e9riels de Bureau",
                "region_execution": "BEJA",
            },
        )
        preferences = TenderPreferences(
            regions=("Tunis",),
            categories=({"category": "Biens", "subcategory": "Mat\u00e9riels informatiques"},),
            max_budget=None,
        )

        result = score_tender(tender, preferences, semantic_similarity=0.50)

        self.assertEqual(result["components"]["region_match"], 0.0)
        self.assertNotIn("Region aligned: Tunis", result["reasons"])

    def test_region_alignment_adds_explicit_reason(self):
        tender = self.create_tender(ville="Tunis")
        preferences = TenderPreferences(
            regions=("Tunis",),
            categories=({"category": "Biens", "subcategory": "Mat\u00e9riels informatiques"},),
            max_budget=None,
        )

        result = score_tender(tender, preferences, semantic_similarity=0.50)

        self.assertEqual(result["components"]["region_match"], 1.0)
        self.assertIn("Region aligned: Tunis", result["reasons"])


class TenderRecommendationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="tender-user",
            email="tender-user@example.com",
            password="test-password",
        )

    def test_tender_recommendations_requires_authentication(self):
        response = self.client.get("/api/opportunities/tenders/recommendations/")

        self.assertEqual(response.status_code, 401)

    @patch("opportunities.views.get_tender_opportunities", return_value=[])
    def test_tender_recommendations_uses_authenticated_user(self, mocked_recommendations):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/opportunities/tenders/recommendations/?limit=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"count": 0, "results": []})
        mocked_recommendations.assert_called_once_with(user=self.user, limit=10)
