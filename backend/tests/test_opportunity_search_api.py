from datetime import date, timedelta

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


class OpportunitySearchApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
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

    def create_opp(self, **kwargs):
        defaults = {
            "titre": "Python Backend Developer",
            "description": "Django APIs and PostgreSQL",
            "organisation_nom": "Acme",
            "ville": "Tunis",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_limite": date.today() + timedelta(days=20),
            "source": self.linkedin,
            "quality_score": 0.8,
            "normalized_work_mode": "REMOTE",
            "experience_min": 2,
            "experience_max": 4,
        }
        defaults.update(kwargs)
        return Opportunite.objects.create(**defaults)

    def test_default_sort_uses_quality_then_recent_publication_date(self):
        older = self.create_opp(
            titre="Older same quality",
            quality_score=0.9,
            date_publication=date.today() - timedelta(days=10),
        )
        newer = self.create_opp(
            titre="Newer same quality",
            quality_score=0.9,
            date_publication=date.today(),
        )
        lower_quality = self.create_opp(
            titre="Newer lower quality",
            quality_score=0.2,
            date_publication=date.today() + timedelta(days=1),
        )

        response = self.client.get("/api/opportunities/", {"sort": "quality"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"][:3]]
        self.assertEqual(ids, [newer.id, older.id, lower_quality.id])

    def test_server_side_filters_and_dynamic_facets_respect_active_filters(self):
        self.create_opp(titre="Remote Job Tunis", ville="Tunis", source=self.linkedin)
        self.create_opp(titre="Hybrid Job Sfax", ville="Sfax", source=self.keejob, normalized_work_mode="HYBRID")
        self.create_opp(titre="Internship Tunis", type_opportunite=TypeOpportunite.STAGE, ville="Tunis")
        self.create_opp(titre="Expired Job", statut=StatutOpportunite.EXPIREE)

        response = self.client.get("/api/opportunities/", {"type": "EMPLOI", "page_size": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertEqual(titles, {"Remote Job Tunis", "Hybrid Job Sfax"})

        location_counts = {item["key"]: item["count"] for item in response.data["facets"]["locations"]}
        self.assertEqual(location_counts["Tunis"], 1)
        self.assertEqual(location_counts["Sfax"], 1)
        type_counts = {item["key"]: item["count"] for item in response.data["facets"]["types"]}
        self.assertEqual(type_counts, {"EMPLOI": 2})

    def test_source_filter_accepts_source_name_and_id(self):
        self.create_opp(titre="LinkedIn role", source=self.linkedin)
        self.create_opp(titre="Keejob role", source=self.keejob)

        by_name = self.client.get("/api/opportunities/", {"source": "Keejob"})
        by_id = self.client.get("/api/opportunities/", {"source": str(self.linkedin.id)})

        self.assertEqual(by_name.status_code, status.HTTP_200_OK)
        self.assertEqual({item["titre"] for item in by_name.data["results"]}, {"Keejob role"})
        self.assertEqual(by_id.status_code, status.HTTP_200_OK)
        self.assertEqual({item["titre"] for item in by_id.data["results"]}, {"LinkedIn role"})

    def test_sector_filter_matches_normalized_industry_and_company_sector_metadata(self):
        finance = self.create_opp(
            titre="Finance Backend",
            normalized_industries=["FINTECH"],
            extra_data={"company_sector": "Banque, assurance"},
        )
        agro = self.create_opp(
            titre="Data Analyst Marketing",
            normalized_industries=[],
            extra_data={"company_sector": "agriculture / agro-alimentaire / environnement"},
        )
        self.create_opp(
            titre="Generic Frontend",
            normalized_industries=[],
            extra_data={"company_sector": "Informatique"},
        )

        finance_response = self.client.get("/api/opportunities/", {"sector": "finance", "page_size": 10})
        agro_response = self.client.get("/api/opportunities/", {"industry": "agroalimentaire", "page_size": 10})

        self.assertEqual(finance_response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in finance_response.data["results"]}, {finance.id})
        self.assertEqual(agro_response.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in agro_response.data["results"]}, {agro.id})

    def test_trigram_search_handles_partial_and_typo_queries(self):
        self.create_opp(titre="Django Backend Engineer", description="Python APIs")
        self.create_opp(titre="Finance Analyst", description="Spreadsheets and reporting")

        response = self.client.get("/api/opportunities/", {"search": "Djanog"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Django Backend Engineer", titles)
        self.assertNotIn("Finance Analyst", titles)

    def test_facets_endpoint_returns_counts_without_results_payload(self):
        self.create_opp(titre="Remote Job", normalized_work_mode="REMOTE")
        self.create_opp(titre="Onsite Job", normalized_work_mode="ON_SITE")

        response = self.client.get("/api/opportunities/facets/", {"work_mode": "REMOTE"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("facets", response.data)
        self.assertNotIn("results", response.data)

    def test_paginated_filter_query_has_bounded_query_count(self):
        for index in range(40):
            self.create_opp(
                titre=f"Python Role {index}",
                ville="Tunis" if index % 2 else "Sfax",
                source=self.linkedin if index % 3 else self.keejob,
                quality_score=(index % 10) / 10,
                normalized_work_mode="REMOTE" if index % 2 else "HYBRID",
            )

        cache.clear()
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(
                "/api/opportunities/",
                {"search": "Python", "type": "EMPLOI", "work_mode": "REMOTE", "page_size": 20},
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(captured), 14)

    def test_search_and_filter_indexes_exist(self):
        expected_indexes = {
            "source_nom_idx",
            "opp_active_quality_date_idx",
            "opp_status_type_quality_date_idx",
            "opp_status_location_quality_date_idx",
            "opp_status_source_quality_date_idx",
            "opp_status_workmode_quality_date_idx",
            "opp_title_trgm_idx",
            "opp_company_trgm_idx",
            "opp_location_trgm_idx",
            "opp_description_trgm_idx",
            "opp_search_vector_gin_idx",
        }

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename IN ('opportunities_opportunite', 'opportunities_sourceopportunite')
                  AND indexname = ANY(%s)
                """,
                [list(expected_indexes)],
            )
            found = {row[0] for row in cursor.fetchall()}

        self.assertEqual(found, expected_indexes)
