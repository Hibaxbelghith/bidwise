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
        first = response.data["results"][0]
        self.assertNotIn("embedding_vector", first)
        self.assertNotIn("embedding_model", first)

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

    def test_similar_endpoint_returns_ranked_results(self):
        model_identifier = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr"
        anchor = self.create_opp(
            titre="Anchor Opportunity",
            embedding_vector=[1.0, 0.0, 0.0],
            embedding_model=model_identifier,
        )
        best_match = self.create_opp(
            titre="Best Match",
            embedding_vector=[0.9, 0.1, 0.0],
            embedding_model=model_identifier,
        )
        second_match = self.create_opp(
            titre="Second Match",
            embedding_vector=[0.6, 0.4, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="Other Model Match",
            embedding_vector=[0.99, 0.0, 0.01],
            embedding_model="BAAI/bge-small-en-v1.5@bench-v1",
        )

        response = self.client.get(f"{self.base_url}{anchor.pk}/similar/", {"k": 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], best_match.pk)
        self.assertEqual(response.data[1]["id"], second_match.pk)
        self.assertLessEqual(response.data[0]["similarity_score"], 1.0)
        self.assertGreaterEqual(
            response.data[0]["similarity_score"],
            response.data[1]["similarity_score"],
        )
        self.assertIn("titre", response.data[0])
        self.assertNotIn("embedding_vector", response.data[0])
        self.assertNotIn("embedding_model", response.data[0])
        returned_ids = {item["id"] for item in response.data}
        self.assertNotIn(anchor.pk, returned_ids)

    def test_similar_endpoint_deduplicates_top_k_by_content_fingerprint(self):
        model_identifier = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr"
        anchor = self.create_opp(
            titre="Anchor",
            description="Role description",
            embedding_vector=[1.0, 0.0, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="TÉLÉCONSEILLERS (APPELS, CHAT & EMAIL)",
            description="Le groupe outsourcia est un opérateur spécialisé dans les métiers de l'outsourcing.",
            embedding_vector=[0.99, 0.01, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="teleconseillers appels chat email",
            description="Le groupe outsourcia est un operateur specialise dans les metiers de l outsourcing.",
            embedding_vector=[0.98, 0.02, 0.0],
            embedding_model=model_identifier,
        )

        response = self.client.get(f"{self.base_url}{anchor.pk}/similar/", {"k": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_similar_endpoint_filters_candidates_by_status_and_type(self):
        model_identifier = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr"
        anchor = self.create_opp(
            titre="Anchor Job",
            type_opportunite=TypeOpportunite.EMPLOI,
            embedding_vector=[1.0, 0.0, 0.0],
            embedding_model=model_identifier,
        )
        active_same_type = self.create_opp(
            titre="Active Same Type",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            embedding_vector=[0.9, 0.1, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="Expired Same Type",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.EXPIREE,
            embedding_vector=[0.95, 0.05, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="Active Different Type",
            type_opportunite=TypeOpportunite.PROJET,
            statut=StatutOpportunite.ACTIVE,
            embedding_vector=[0.93, 0.07, 0.0],
            embedding_model=model_identifier,
        )

        response = self.client.get(f"{self.base_url}{anchor.pk}/similar/", {"k": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in response.data]
        self.assertEqual(returned_ids, [active_same_type.pk])

    def test_similar_endpoint_returns_empty_list_when_source_has_no_embedding(self):
        anchor = self.create_opp(titre="No Embedding Anchor", embedding_vector=None, embedding_model="")
        self.create_opp(
            titre="Candidate",
            embedding_vector=[1.0, 0.0, 0.0],
            embedding_model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr",
        )

        response = self.client.get(f"{self.base_url}{anchor.pk}/similar/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_similar_endpoint_top_k_alias_is_supported(self):
        model_identifier = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr"
        anchor = self.create_opp(
            titre="Anchor Top K Alias",
            embedding_vector=[1.0, 0.0, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="Top K Candidate 1",
            embedding_vector=[0.9, 0.1, 0.0],
            embedding_model=model_identifier,
        )
        self.create_opp(
            titre="Top K Candidate 2",
            embedding_vector=[0.8, 0.2, 0.0],
            embedding_model=model_identifier,
        )

        response = self.client.get(f"{self.base_url}{anchor.pk}/similar/", {"top_k": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_similar_endpoint_returns_404_for_unknown_opportunity(self):
        response = self.client.get(f"{self.base_url}999999/similar/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
