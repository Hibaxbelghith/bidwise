from datetime import date, timedelta

from django.db import connection, models
from django.db.utils import IntegrityError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from users.models import Utilisateur

from .models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from .scraping.pipeline import run_collection
from .scraping.scraper_base import BaseOpportunityScraper
from .serializers import OpportuniteSerializer


class OpportuniteModelMetaTests(TestCase):
    def test_unique_constraint_exists_for_title_source_publication(self):
        unique_constraints = [
            tuple(constraint.fields)
            for constraint in Opportunite._meta.constraints
            if isinstance(constraint, models.UniqueConstraint)
        ]
        self.assertIn(("titre", "source", "date_publication"), unique_constraints)

    def test_expected_indexes_exist(self):
        index_fields = {tuple(index.fields) for index in Opportunite._meta.indexes}
        self.assertIn(("type_opportunite", "statut"), index_fields)
        self.assertIn(("statut",), index_fields)
        self.assertIn(("date_publication",), index_fields)
        self.assertIn(("date_limite",), index_fields)
        self.assertIn(("date_creation",), index_fields)
        self.assertIn(("statut", "date_publication"), index_fields)

    def test_duplicate_opportunity_same_triplet_is_blocked(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )
        Opportunite.objects.create(
            titre="Backend Engineer",
            description="Desc",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        with self.assertRaises(IntegrityError):
            Opportunite.objects.create(
                titre="Backend Engineer",
                description="Another desc",
                type_opportunite=TypeOpportunite.EMPLOI,
                statut=StatutOpportunite.ACTIVE,
                date_publication=date.today(),
                source=source,
            )


class OpportuniteSerializerTests(TestCase):
    def setUp(self):
        self.source = SourceOpportunite.objects.create(
            nom="Indeed",
            url="https://indeed.com",
            type_source="SITE_EMPLOI",
        )

    def test_validate_deadline_not_before_publication(self):
        serializer = OpportuniteSerializer(
            data={
                "titre": "Bad Dates",
                "description": "Desc",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "date_publication": "2026-03-10",
                "date_limite": "2026-03-01",
                "source_id": self.source.pk,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("date_limite", serializer.errors)

    def test_read_only_owner_field_ignores_payload_owner(self):
        owner = Utilisateur.objects.create_user(username="owner", password="pass1234")
        serializer = OpportuniteSerializer(
            data={
                "titre": "Owner Test",
                "description": "Desc",
                "organisation_nom": "Orange Tunisie",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "date_publication": "2026-03-10",
                "source_id": self.source.pk,
                "organisation": owner.pk,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("organisation", serializer.validated_data)
        self.assertEqual(serializer.validated_data["organisation_nom"], "Orange Tunisie")


class OpportuniteAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = Utilisateur.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="pass1234",
        )
        self.other_user = Utilisateur.objects.create_user(
            username="other",
            email="other@test.com",
            password="pass1234",
        )
        self.staff_user = Utilisateur.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass1234",
            is_staff=True,
        )
        self.source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.com",
            type_source="SITE_EMPLOI",
        )
        self.base_url = "/api/opportunities/"
        self.legacy_url = "/api/opportunites/"
        self.sources_url = "/api/sources/"

    def create_opp(self, **kwargs):
        defaults = {
            "titre": "Default Opportunity",
            "description": "Django and APIs",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_limite": date.today() + timedelta(days=15),
            "organisation": self.owner,
            "source": self.source,
        }
        defaults.update(kwargs)
        return Opportunite.objects.create(**defaults)

    def test_list_is_public(self):
        self.create_opp()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_detail_is_public(self):
        opportunity = self.create_opp(statut=StatutOpportunite.EXPIREE)
        response = self.client.get(f"{self.base_url}{opportunity.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], opportunity.pk)

    def test_create_requires_authentication(self):
        response = self.client.post(
            self.base_url,
            {
                "titre": "Unauthorized create",
                "description": "Desc",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "date_publication": date.today().isoformat(),
                "source_id": self.source.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_binds_owner_from_authenticated_user(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            self.base_url,
            {
                "titre": "Secure ownership",
                "description": "Desc",
                "organisation_nom": "Acme Corp",
                "type_opportunite": TypeOpportunite.STAGE,
                "date_publication": date.today().isoformat(),
                "source_id": self.source.pk,
                "organisation": self.other_user.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(pk=response.data["id"])
        self.assertEqual(opportunity.organisation_id, self.owner.pk)
        self.assertEqual(opportunity.organisation_nom, "Acme Corp")

    def test_non_owner_cannot_update(self):
        opportunity = self.create_opp()
        self.client.force_authenticate(self.other_user)
        response = self.client.patch(
            f"{self.base_url}{opportunity.pk}/",
            {"titre": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update(self):
        opportunity = self.create_opp()
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"{self.base_url}{opportunity.pk}/",
            {"titre": "Updated Title"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.titre, "Updated Title")

    def test_default_list_returns_only_active(self):
        self.create_opp(titre="Active", statut=StatutOpportunite.ACTIVE)
        self.create_opp(titre="Expired", statut=StatutOpportunite.EXPIREE)

        response = self.client.get(self.base_url)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Active", titles)
        self.assertNotIn("Expired", titles)

    def test_status_filter_allows_non_active_records(self):
        self.create_opp(titre="Active", statut=StatutOpportunite.ACTIVE)
        self.create_opp(titre="Expired", statut=StatutOpportunite.EXPIREE)

        response = self.client.get(self.base_url, {"statut": StatutOpportunite.EXPIREE})
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Expired", titles)
        self.assertNotIn("Active", titles)

    def test_status_alias_filter_works(self):
        self.create_opp(titre="Archived", statut=StatutOpportunite.ARCHIVEE)
        response = self.client.get(self.base_url, {"status": StatutOpportunite.ARCHIVEE})
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Archived", titles)

    def test_search_uses_title_and_description(self):
        self.create_opp(titre="Python Engineer", description="Backend APIs")
        self.create_opp(titre="Data Analyst", description="Django pipelines")

        response_title = self.client.get(self.base_url, {"search": "Python"})
        title_results = {item["titre"] for item in response_title.data["results"]}
        self.assertIn("Python Engineer", title_results)
        self.assertNotIn("Data Analyst", title_results)

        response_description = self.client.get(self.base_url, {"search": "pipelines"})
        description_results = {item["titre"] for item in response_description.data["results"]}
        self.assertIn("Data Analyst", description_results)
        self.assertNotIn("Python Engineer", description_results)

    def test_ordering_by_publication_date(self):
        self.create_opp(titre="Old", date_publication=date.today() - timedelta(days=10))
        self.create_opp(titre="New", date_publication=date.today())

        response = self.client.get(self.base_url, {"ordering": "-date_publication"})
        titles = [item["titre"] for item in response.data["results"]]
        self.assertEqual(titles[0], "New")

    def test_page_size_is_capped_to_50(self):
        for index in range(60):
            self.create_opp(
                titre=f"Opportunity {index}",
                date_publication=date.today() - timedelta(days=index),
            )

        response = self.client.get(self.base_url, {"page_size": 100})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["results"]), 50)

    def test_english_and_legacy_routes_are_both_available(self):
        self.create_opp()
        english_response = self.client.get(self.base_url)
        legacy_response = self.client.get(self.legacy_url)
        self.assertEqual(english_response.status_code, status.HTTP_200_OK)
        self.assertEqual(legacy_response.status_code, status.HTTP_200_OK)
        self.assertEqual(english_response.data["count"], legacy_response.data["count"])

    def test_source_read_is_public_but_write_requires_admin(self):
        public_read = self.client.get(self.sources_url)
        self.assertEqual(public_read.status_code, status.HTTP_200_OK)

        non_admin_response = self.client.post(
            self.sources_url,
            {"nom": "X", "url": "https://x.com", "type_source": "AUTRE"},
            format="json",
        )
        self.assertEqual(non_admin_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.staff_user)
        admin_response = self.client.post(
            self.sources_url,
            {"nom": "Admin Source", "url": "https://admin.com", "type_source": "AUTRE"},
            format="json",
        )
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)

    def test_select_related_prevents_n_plus_one_on_list(self):
        for index in range(5):
            source = SourceOpportunite.objects.create(
                nom=f"Source {index}",
                url=f"https://source-{index}.com",
                type_source="AUTRE",
            )
            self.create_opp(
                titre=f"Opportunity {index}",
                source=source,
                date_publication=date.today() - timedelta(days=index),
            )

        with CaptureQueriesContext(connection) as context:
            response = self.client.get(self.base_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertLessEqual(len(context), 5)


class PipelineTests(TestCase):
    def test_pipeline_uses_upsert_on_duplicate_triplet(self):
        class DuplicateScraper(BaseOpportunityScraper):
            source_name = "Keejob"
            source_url = "https://www.keejob.com/offres-emploi/"
            source_type = "SITE_EMPLOI"

            def fetch_raw_records(self):
                return [
                    {
                        "title": "Duplicate title",
                        "description": "Version 1",
                        "organization": "Company A",
                        "opportunity_type": "job",
                        "status": "active",
                        "publication_date": "2026-03-10",
                    },
                    {
                        "title": "Duplicate title",
                        "description": "Version 2",
                        "organization": "Company B",
                        "opportunity_type": "job",
                        "status": "active",
                        "publication_date": "2026-03-10",
                    },
                ]

        stats = run_collection(DuplicateScraper())
        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["skipped"], 0)

        self.assertEqual(Opportunite.objects.count(), 1)
        opportunity = Opportunite.objects.first()
        self.assertEqual(opportunity.description, "version 2")
        self.assertEqual(opportunity.organisation_nom, "Company B")

    def test_pipeline_skips_invalid_records(self):
        class InvalidScraper(BaseOpportunityScraper):
            source_name = "Keejob"
            source_url = "https://www.keejob.com/offres-emploi/"
            source_type = "SITE_EMPLOI"

            def fetch_raw_records(self):
                return [
                    {
                        "title": "",
                        "description": "Missing title",
                        "opportunity_type": "job",
                        "publication_date": "2026-03-10",
                    }
                ]

        stats = run_collection(InvalidScraper())
        self.assertEqual(stats["created"], 0)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(stats["skipped"], 1)
        self.assertEqual(Opportunite.objects.count(), 0)
