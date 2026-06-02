from datetime import date, timedelta
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.db import connection, models
from django.db.utils import IntegrityError
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from opportunities.enrichment import enrich_opportunity_text
from opportunities.materialization import materialize_opportunity
from opportunities.models import (
    Opportunite,
    PipelineRun,
    PipelineRunStatus,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from opportunities.normalization import normalize_raw_opportunity
from opportunities.scraping import pipeline as scraping_pipeline
from opportunities.scraping.pipeline import run_collection
from opportunities.scraping.scraper_base import BaseOpportunityScraper
from opportunities.scraping.sources import EmploiTunisieScraper
from opportunities.serializers import OpportuniteSerializer
from opportunities.utils.images import DEFAULT_COMPANY_LOGO_URL
from opportunities.utils.text_parsing import parse_experience_bounds
from users.models import Utilisateur


class OpportuniteModelMetaTests(TestCase):
    def test_unique_constraint_exists_for_source_item_url_per_source(self):
        unique_constraints = [
            tuple(constraint.fields)
            for constraint in Opportunite._meta.constraints
            if isinstance(constraint, models.UniqueConstraint)
        ]
        self.assertIn(("source", "source_item_url"), unique_constraints)

    def test_expected_indexes_exist(self):
        index_fields = {tuple(index.fields) for index in Opportunite._meta.indexes}
        self.assertIn(("type_opportunite", "statut"), index_fields)
        self.assertIn(("statut",), index_fields)
        self.assertIn(("date_publication",), index_fields)
        self.assertIn(("date_limite",), index_fields)
        self.assertIn(("date_creation",), index_fields)
        self.assertIn(("statut", "date_publication"), index_fields)

    def test_duplicate_opportunity_same_source_url_is_blocked(self):
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
            source_item_url="https://www.keejob.com/offres-emploi/123/backend-engineer/",
            source=source,
        )

        with self.assertRaises(IntegrityError):
            Opportunite.objects.create(
                titre="Backend Engineer duplicate",
                description="Another desc",
                type_opportunite=TypeOpportunite.EMPLOI,
                statut=StatutOpportunite.ACTIVE,
                date_publication=date.today(),
                source_item_url="https://www.keejob.com/offres-emploi/123/backend-engineer/",
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

    def test_serializer_city_output_is_canonicalized(self):
        opportunity = Opportunite.objects.create(
            titre="City Canonical",
            description="Desc",
            ville="Centre ville, Tunis",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=self.source,
        )

        payload = OpportuniteSerializer(opportunity).data
        self.assertEqual(payload["ville"], "Tunis")

    def test_serializer_exposes_extra_data(self):
        opportunity = Opportunite.objects.create(
            titre="Tender Detail",
            description="Desc",
            ville="Ben Arous",
            organisation_nom="Municipalité Ben Arous",
            extra_data={"procedure": "Appel d'offres ouvert", "pdf_url": "https://example.org/avis.docx"},
            type_opportunite=TypeOpportunite.PROJET,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=self.source,
        )

        payload = OpportuniteSerializer(opportunity).data
        self.assertEqual(payload["extra_data"]["procedure"], "Appel d'offres ouvert")

    def test_serializer_exposes_default_logo_and_newness_fields(self):
        opportunity = Opportunite.objects.create(
            titre="No Logo",
            description="Desc",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=self.source,
        )

        payload = OpportuniteSerializer(opportunity).data

        self.assertEqual(payload["company_logo"], DEFAULT_COMPANY_LOGO_URL)
        self.assertEqual(payload["last_updated_at"], payload["date_modification"])
        self.assertTrue(payload["is_new"])

    def test_serializer_uses_default_logo_for_anonymous_company(self):
        opportunity = Opportunite.objects.create(
            titre="Anonymous Logo",
            description="Desc",
            organisation_nom="Entreprise Anonyme",
            company_logo="https://www.keejob.com/media/recruiter/recruiter_73/logo.png",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=self.source,
        )

        payload = OpportuniteSerializer(opportunity).data

        self.assertEqual(payload["company_logo"], DEFAULT_COMPANY_LOGO_URL)


class RawNormalizationTests(TestCase):
    def setUp(self):
        self.source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

    def _create_raw(self, location):
        return RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Backend Engineer",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": location,
                "url": "https://www.keejob.com/offres-emploi/sample/",
            },
            raw_titre="Backend Engineer",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash=f"hash-{location}",
        )

    def test_city_normalization_rule_based_variants(self):
        variants = [
            "La Marsa, Tunis",
            "Centre ville, Tunis",
            "Tunis, Ariana",
        ]

        for location in variants:
            with self.subTest(location=location):
                raw_obj = self._create_raw(location)
                normalized = normalize_raw_opportunity(raw_obj)
                self.assertEqual(normalized["ville"], "Tunis")

    def test_city_prefers_explicit_city_over_generic_location(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Délégué Médical",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Ben Arous",
                "city": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-city-priority/",
            },
            raw_titre="Délégué Médical",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-city-priority",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["ville"], "Tunis")

    def test_emploi_structured_skills_are_preserved(self):
        emploi_source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        raw_obj = RawOpportunite.objects.create(
            source=emploi_source,
            raw_payload={
                "title": "Délégué Médical",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "skills": ["Laboratoire", "Commercialisation", "Santé", "Commercialisation"],
                "url": "https://www.emploitunisie.com/offre-emploi-tunisie/sample-skills/",
            },
            raw_titre="Délégué Médical",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-emploi-structured-skills",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["skills"], ["Laboratoire", "Commercialisation", "Santé"])

    def test_normalization_handles_missing_extra_data(self):
        linkedin_source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://www.linkedin.com",
            type_source="SITE_EMPLOI",
        )

        raw_obj = RawOpportunite.objects.create(
            source=linkedin_source,
            raw_payload={
                "title": "Backend Engineer",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "company_sector": "Software",
                "extra_data": None,
                "url": "https://www.linkedin.com/jobs/view/123",
            },
            raw_titre="Backend Engineer",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-linkedin-missing-extra-data",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["titre"], "Backend Engineer")
        self.assertIsNone(normalized["extra_data"])

    def test_status_becomes_expired_when_deadline_is_in_past(self):
        generic_source = SourceOpportunite.objects.create(
            nom="Indeed",
            url="https://www.indeed.com",
            type_source="SITE_EMPLOI",
        )
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        raw_obj = RawOpportunite.objects.create(
            source=generic_source,
            raw_payload={
                "title": "Backend Engineer",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "date_limite": yesterday,
                "location": "Tunis",
                "url": "https://www.indeed.com/viewjob?jk=123",
            },
            raw_titre="Backend Engineer",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            raw_date_limite=yesterday,
            payload_hash="hash-past-deadline",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["statut"], StatutOpportunite.EXPIREE)

    def test_keejob_status_stays_active_when_only_deadline_is_in_past(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Backend Engineer",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "date_limite": yesterday,
                "location": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-active-deadline/",
            },
            raw_titre="Backend Engineer",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            raw_date_limite=yesterday,
            payload_hash="hash-keejob-past-deadline-no-badge",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["statut"], StatutOpportunite.ACTIVE)

    def test_source_item_url_is_canonicalized_for_identity(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Data Analyst",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "HTTPS://WWW.KEEJOB.COM/offres-emploi/sample//?utm_source=mail&b=2&a=1",
            },
            raw_titre="Data Analyst",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-canonical-url",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(
            normalized["source_item_url"],
            "https://www.keejob.com/offres-emploi/sample?a=1&b=2",
        )

    def test_normalization_assigns_default_logo_when_image_is_missing_or_invalid(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Backend Engineer",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "company_logo": "javascript:alert(1)",
                "url": "https://www.keejob.com/offres-emploi/logo-default/",
            },
            raw_titre="Backend Engineer",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-logo-default",
        )

        normalized = normalize_raw_opportunity(raw_obj)

        self.assertEqual(normalized["company_logo"], DEFAULT_COMPANY_LOGO_URL)

    def test_keejob_saisonnier_requires_strict_contract_type(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Agent relation client",
                "description": "Description suffisamment longue avec mention de primes saisonnieres.",
                "type_opportunite": "saisonnier",
                "contract_type": "CDD",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-seasonal/",
            },
            raw_titre="Agent relation client",
            raw_description="Description suffisamment longue avec mention de primes saisonnieres.",
            raw_type="saisonnier",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-keejob-seasonal-contract-cdd",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["type_opportunite"], TypeOpportunite.EMPLOI)

    def test_keejob_saisonnier_kept_when_contract_type_is_saisonnier(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Agent saisonnier",
                "description": "Description suffisamment longue pour normalisation.",
                "type_opportunite": "saisonnier",
                "contract_type": "SAISONNIER",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-seasonal-strict/",
            },
            raw_titre="Agent saisonnier",
            raw_description="Description suffisamment longue pour normalisation.",
            raw_type="saisonnier",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-keejob-seasonal-contract-strict",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["type_opportunite"], TypeOpportunite.SAISONNIER)

    def test_keejob_contract_type_invalid_is_dropped(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Agent Support",
                "description": "Description suffisamment longue pour normalisation backend.",
                "type_opportunite": "emploi",
                "contract_type": "Lieu du travail",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-contract-invalid/",
            },
            raw_titre="Agent Support",
            raw_description="Description suffisamment longue pour normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-keejob-contract-invalid",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertIsNone(normalized["contract_type"])

    def test_keejob_contract_type_stage_pfe_is_normalized(self):
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={
                "title": "Stagiaire QA",
                "description": "Description suffisamment longue pour normalisation backend.",
                "type_opportunite": "stage",
                "contract_type": "stage/pfe",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.keejob.com/offres-emploi/sample-contract-stage-pfe/",
            },
            raw_titre="Stagiaire QA",
            raw_description="Description suffisamment longue pour normalisation backend.",
            raw_type="stage",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-keejob-contract-stage-pfe",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["contract_type"], "Stage/PFE")

    def test_emploi_multi_value_experience_is_normalized_to_min_max(self):
        emploi_source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        raw_obj = RawOpportunite.objects.create(
            source=emploi_source,
            raw_payload={
                "title": "Community Manager",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "contract_type": "CDI - Temps partiel",
                "experience": "Débutant < 2 ans - Expérience entre 2 ans et 5 ans - Expérience entre 5 ans et 10 ans - Expérience > 10 ans",
                "education_level": "Bac+2 - Bac+3 - Bac+4 - Bac+5 et plus",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.emploitunisie.com/offre-emploi-tunisie/sample/",
            },
            raw_titre="Community Manager",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-emploi-multi-experience",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["experience_min"], 0)
        self.assertIsNone(normalized["experience_max"])

    def test_emploi_multi_range_with_open_ended_keeps_lowest_min(self):
        emploi_source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        raw_obj = RawOpportunite.objects.create(
            source=emploi_source,
            raw_payload={
                "title": "Ingénieur Cybersécurité",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "contract_type": "Freelance",
                "experience": "Expérience entre 2 ans et 5 ans - Expérience entre 5 ans et 10 ans - Expérience > 10 ans",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunisie",
                "url": "https://www.emploitunisie.com/offre-emploi-tunisie/sample-cybershore/",
            },
            raw_titre="Ingénieur Cybersécurité",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-emploi-cybershore-experience",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["experience_min"], 2)
        self.assertIsNone(normalized["experience_max"])

    def test_emploi_contract_and_education_lists_are_derived(self):
        emploi_source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        raw_obj = RawOpportunite.objects.create(
            source=emploi_source,
            raw_payload={
                "title": "Chargé marketing",
                "description": "Description suffisamment longue pour la normalisation backend.",
                "type_opportunite": "emploi",
                "contract_type": "CDI - Temps partiel",
                "education_level": "Bac+2 - Bac+3 - Bac+4 - Bac+5 et plus",
                "statut": "active",
                "publication_date": "2026-04-10",
                "location": "Tunis",
                "url": "https://www.emploitunisie.com/offre-emploi-tunisie/sample-contract/",
            },
            raw_titre="Chargé marketing",
            raw_description="Description suffisamment longue pour la normalisation backend.",
            raw_type="emploi",
            raw_status="active",
            raw_date_publication="2026-04-10",
            payload_hash="hash-emploi-contract-education",
        )

        normalized = normalize_raw_opportunity(raw_obj)
        self.assertEqual(normalized["contract_types"], ["CDI", "Temps partiel"])
        self.assertEqual(normalized["education_levels"], ["Bac+2", "Bac+3", "Bac+4", "Bac+5"])


class EmploiTunisieScraperStructuredParsingTests(TestCase):
        def setUp(self):
                self.scraper = EmploiTunisieScraper(max_pages=1, fetch_details=True)

        def test_summary_parser_uses_icon_classes_without_position_dependency(self):
                soup = BeautifulSoup(
                        """
                        <div class="card-block-summary">
                            <ul>
                                <li class="withicon file-signature"><span>CDI - Temps partiel</span></li>
                                <li class="withicon graduation-cap"><span>Bac+3</span></li>
                                <li class="withicon chart"><span>Expérience entre 2 ans et 5 ans</span></li>
                                <li class="withicon map-marker-alt"><span>Sfax</span></li>
                            </ul>
                        </div>
                        """,
                        "html.parser",
                )

                structured = self.scraper._extract_structured_fields_from_summary(soup)

                self.assertEqual(structured["contract_type"], "CDI - Temps partiel")
                self.assertEqual(structured["education_level"], "Bac+3")
                self.assertEqual(structured["experience"], "Expérience entre 2 ans et 5 ans")
                self.assertEqual(structured["location_region"], "Sfax")

        def test_summary_parser_ignores_plain_years_without_experience_context(self):
                soup = BeautifulSoup(
                        """
                        <div class="card-block-summary">
                            <ul>
                                <li><span>23 ans</span></li>
                                <li class="withicon file-signature"><span>CDI</span></li>
                            </ul>
                        </div>
                        """,
                        "html.parser",
                )

                structured = self.scraper._extract_structured_fields_from_summary(soup)

                self.assertIsNone(structured["experience"])
                self.assertEqual(structured["contract_type"], "CDI")

        def test_detail_block_has_priority_over_summary_for_core_fields(self):
                soup = BeautifulSoup(
                        """
                        <div class="card-block-summary">
                            <ul>
                                <li class="withicon chart"><span>Expérience entre 2 ans et 5 ans</span></li>
                                <li class="withicon file-signature"><span>CDD</span></li>
                                <li class="withicon graduation-cap"><span>Bac+3</span></li>
                            </ul>
                        </div>
                        <ul class="arrow-list">
                            <li><strong>Type de contrat</strong><span>CDI</span></li>
                            <li><strong>Niveau d'expérience</strong><span>Débutant &lt; 2 ans</span></li>
                            <li><strong>Région</strong><span>Tunis</span></li>
                            <li><strong>Métier</strong><span>Production, maintenance, qualité</span></li>
                            <li><strong>Secteur d'activité</strong><span>Industrie</span></li>
                        </ul>
                        <ul class="skills"><li>Qualité</li></ul>
                        """,
                        "html.parser",
                )

                structured = self.scraper._extract_detail_structured_fields(soup)

                self.assertEqual(structured["contract_type"], "CDI")
                self.assertEqual(structured["experience"], "Débutant < 2 ans")
                self.assertEqual(structured["education_level"], "Bac+3")
                self.assertEqual(structured["location_region"], "Tunis")
                self.assertEqual(structured["job_category"], "Production, maintenance, qualité")
                self.assertEqual(structured["company_sector"], "Industrie")
                self.assertEqual(structured["skills"], ["Qualité"])

        def test_detail_block_extracts_salary_value(self):
                soup = BeautifulSoup(
                        """
                        <ul class="arrow-list">
                            <li><strong>Salaire proposé</strong><span>1 800 - 2 400 TND</span></li>
                        </ul>
                        """,
                        "html.parser",
                )

                structured = self.scraper._extract_detail_structured_fields(soup)
                self.assertEqual(structured["salary"], "1 800 - 2 400 TND")

        def test_detail_description_html_is_extracted_and_sanitized(self):
                soup = BeautifulSoup(
                        """
                        <article class="page-application-content">
                            <section>
                                <div class="job-description">
                                    <h3>Missions</h3>
                                    <p>Garantir les politiques qualité et énergie.</p>
                                    <ol>
                                        <li>Piloter le système qualité</li>
                                    </ol>
                                    <script>alert('x')</script>
                                </div>
                            </section>
                        </article>
                        """,
                        "html.parser",
                )

                description_html = self.scraper._extract_detail_description_html(soup)

                self.assertNotIn("<script", description_html.lower())
                self.assertIn("<strong>Missions</strong>", description_html)
                self.assertIn("<ul>", description_html)

                cleaned_soup = BeautifulSoup(f"<div>{description_html}</div>", "html.parser")
                li = cleaned_soup.select_one("ul li")
                self.assertIsNotNone(li)
                self.assertEqual(li.get_text(" ", strip=True), "Piloter le système qualité")

                description_text = self.scraper._extract_detail_description(soup, description_html)
                self.assertIn("Missions", description_text)
                self.assertIn("Garantir les politiques qualité et énergie.", description_text)

        def test_listing_parser_extracts_fields_from_icon_classes(self):
                soup = BeautifulSoup(
                        """
                        <div class="card-job">
                            <div class="card-job-detail">
                                <ul>
                                    <li class="withicon chart"><span>Expérience entre 2 ans et 5 ans</span></li>
                                    <li class="withicon graduation-cap"><span>Bac+2 - Bac+3</span></li>
                                    <li class="withicon file-signature"><span>CDI - Temps partiel</span></li>
                                    <li class="withicon map-marker-alt"><span>Tunis</span></li>
                                    <li class="withicon briefcase"><span>Production, maintenance, qualité</span></li>
                                </ul>
                            </div>
                        </div>
                        """,
                        "html.parser",
                )

                card = soup.select_one("div.card-job")
                structured = self.scraper._extract_structured_fields(card)

                self.assertEqual(structured["experience"], "Expérience entre 2 ans et 5 ans")
                self.assertEqual(structured["education_level"], "Bac+2 - Bac+3")
                self.assertEqual(structured["contract_type"], "CDI - Temps partiel")
                self.assertEqual(structured["location"], "Tunis")
                self.assertEqual(structured["job_category"], "Production, maintenance, qualité")


class OpportunityTextEnrichmentTests(TestCase):
    def test_enrichment_extracts_salary_experience_skills_and_languages(self):
        payload = {
            "description": "Profil Python/Django avec SQL. Salaire 1200-1800 TND. 3 years d'experience. Langues: anglais et arabe."
        }

        enriched = enrich_opportunity_text(payload)

        self.assertEqual(enriched["salary"], "1200 - 1800 TND")
        self.assertEqual(enriched["experience_min"], 3)
        self.assertEqual(enriched["experience_max"], 3)
        self.assertEqual(enriched["experience_years"], 3)
        self.assertIn("python", enriched["skills"])
        self.assertIn("django", enriched["skills"])
        self.assertIn("sql", enriched["skills"])
        self.assertEqual(enriched["languages_fallback"], ["anglais", "arabe"])

    def test_enrichment_keeps_safe_defaults_when_description_missing(self):
        enriched = enrich_opportunity_text({"description": None})
        self.assertEqual(enriched["salary"], None)
        self.assertEqual(enriched["experience_min"], None)
        self.assertEqual(enriched["experience_max"], None)
        self.assertEqual(enriched["experience_years"], None)
        self.assertEqual(enriched["skills"], [])
        self.assertEqual(enriched["languages_fallback"], None)

    def test_enrichment_uses_structured_salary_but_not_structured_experience(self):
        payload = {
            "description": "Poste logistique.",
            "salary": "700 -1000 TND / Mois",
            "experience": "Entre 2 et 5 ans",
        }

        enriched = enrich_opportunity_text(payload)

        self.assertEqual(enriched["salary"], "700 - 1000 TND")
        self.assertIsNone(enriched["experience_min"])
        self.assertIsNone(enriched["experience_max"])
        self.assertIsNone(enriched["experience_years"])

    def test_enrichment_does_not_override_structured_languages(self):
        payload = {
            "description": "Mission fullstack. Anglais requis.",
            "languages": ["français"],
        }

        enriched = enrich_opportunity_text(payload)
        self.assertEqual(enriched["languages_fallback"], None)

    def test_shared_parser_maps_keejob_structured_experience_values(self):
        cases = {
            "Aucune expérience": (0, 0),
            "Moins d'un an": (0, 1),
            "Entre 1 et 2 ans": (1, 2),
            "Entre 2 et 5 ans": (2, 5),
            "Entre 5 et 10 ans": (5, 10),
            "Plus que 10 ans": (10, None),
        }

        for experience_value, expected in cases.items():
            with self.subTest(experience=experience_value):
                parsed_min, parsed_max = parse_experience_bounds(experience_value)
                enriched = enrich_opportunity_text(
                    {
                        "description": "Description générique.",
                        "experience": experience_value,
                    }
                )
                self.assertEqual(parsed_min, expected[0])
                self.assertEqual(parsed_max, expected[1])
                self.assertIsNone(enriched["experience_min"])
                self.assertIsNone(enriched["experience_max"])

    def test_enrichment_prefers_existing_normalized_experience_bounds(self):
        payload = {
            "description": "Description générique.",
            "experience": "Entre 2 et 5 ans",
            "experience_min": 0,
            "experience_max": None,
        }

        enriched = enrich_opportunity_text(payload)

        self.assertEqual(enriched["experience_min"], 0)
        self.assertIsNone(enriched["experience_max"])
        self.assertEqual(enriched["experience_years"], 0)

    def test_shared_parser_parses_multi_value_structured_experience(self):
        payload = {
            "description": "Description générique.",
            "experience": "Débutant < 2 ans - Expérience entre 2 ans et 5 ans - Expérience > 10 ans",
        }

        parsed_min, parsed_max = parse_experience_bounds(payload["experience"])
        enriched = enrich_opportunity_text(payload)

        self.assertEqual(parsed_min, 0)
        self.assertIsNone(parsed_max)
        self.assertIsNone(enriched["experience_min"])
        self.assertIsNone(enriched["experience_max"])

    def test_shared_parser_keeps_lowest_min_for_multi_range_with_open_ended(self):
        payload = {
            "description": "Description générique.",
            "experience": "Expérience entre 2 ans et 5 ans - Expérience entre 5 ans et 10 ans - Expérience > 10 ans",
        }

        parsed_min, parsed_max = parse_experience_bounds(payload["experience"])
        enriched = enrich_opportunity_text(payload)

        self.assertEqual(parsed_min, 2)
        self.assertIsNone(parsed_max)
        self.assertIsNone(enriched["experience_min"])
        self.assertIsNone(enriched["experience_max"])

    def test_enrichment_caps_unreasonable_structured_experience_max(self):
        payload = {
            "description": "Description générique.",
            "experience": "Entre 2 et 35 ans",
            "experience_min": 2,
            "experience_max": 35,
        }

        enriched = enrich_opportunity_text(payload)

        self.assertEqual(enriched["experience_min"], 2)
        self.assertIsNone(enriched["experience_max"])

    def test_enrichment_merges_structured_and_detected_skills(self):
        payload = {
            "description": "Compétences techniques: Python et SQL.",
            "skills": ["Marketing Digital", "python"],
        }

        enriched = enrich_opportunity_text(payload)

        self.assertIn("Marketing Digital", enriched["skills"])
        self.assertIn("python", enriched["skills"])
        self.assertIn("sql", enriched["skills"])
        self.assertEqual(enriched["skills"].count("python"), 1)

    def test_enrichment_uses_job_qualifications_for_salary_and_skills(self):
        payload = {
            "description": "Poste cybersécurité.",
            "job_qualifications": "Kali Linux, Burp Suite, Metasploit, Wireshark, AWS, Azure. Salaire proposé : 1 800 - 2 400 TND",
            "skills": ["aws"],
        }

        enriched = enrich_opportunity_text(payload)

        self.assertEqual(enriched["salary"], "1800 - 2400 TND")
        self.assertIn("kali linux", enriched["skills"])
        self.assertIn("burp suite", enriched["skills"])
        self.assertIn("metasploit", enriched["skills"])
        self.assertIn("wireshark", enriched["skills"])
        self.assertIn("aws", enriched["skills"])
        self.assertIn("azure", enriched["skills"])

    def test_enrichment_ignores_company_age_false_positive(self):
        payload = {
            "description": "3C Etudes - depuis 23 ans notre entreprise accompagne ses clients.",
        }

        enriched = enrich_opportunity_text(payload)

        self.assertIsNone(enriched["experience_min"])
        self.assertIsNone(enriched["experience_max"])
        self.assertIsNone(enriched["experience_years"])

    def test_enrichment_ignores_forte_de_plus_de_experience_false_positive(self):
        payload = {
            "description": "Forte de plus de 24 ans d'expérience, l'entreprise accompagne ses clients.",
        }

        enriched = enrich_opportunity_text(payload)

        self.assertIsNone(enriched["experience_min"])
        self.assertIsNone(enriched["experience_max"])
        self.assertIsNone(enriched["experience_years"])

    def test_enrichment_parses_salary_entre_dinars_format(self):
        payload = {
            "description": "Rémunération entre 1 000 et 2 000 dinars selon profil.",
        }

        enriched = enrich_opportunity_text(payload)
        self.assertEqual(enriched["salary"], "1000 - 2000 TND")


class OpportunityMaterializationTests(TestCase):
    def test_materialization_syncs_legacy_experience_to_range(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        normalized_data = {
            "raw_id": 999,
            "source": source,
            "titre": "Backend Developer",
            "description": "Description suffisamment longue pour passer la quality gate et persister la fiche sans rejet.",
            "organisation_nom": "Acme",
            "ville": "Tunis",
            "source_item_url": "https://jobboard.example/opportunity/1",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": 3,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        opportunity = materialize_opportunity(normalized_data)

        self.assertEqual(opportunity.experience_years, 3)
        self.assertEqual(opportunity.experience_min, 3)
        self.assertEqual(opportunity.experience_max, 3)

    def test_materialization_persists_logo_and_description_html(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        normalized_data = {
            "raw_id": 1000,
            "source": source,
            "titre": "Backend Developer",
            "description": "Description suffisamment longue pour passer la quality gate et persister la fiche sans rejet.",
            "description_html": "<h3>Missions</h3><ul><li>Develop APIs</li></ul>",
            "organisation_nom": "Acme",
            "company_logo": "https://jobboard.example/media/acme/logo.png",
            "extra_data": {"procedure": "Appel d'offres ouvert", "pdf_url": "https://jobboard.example/avis.docx"},
            "ville": "Tunis",
            "source_item_url": "https://jobboard.example/opportunity/2",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        opportunity = materialize_opportunity(normalized_data)

        self.assertEqual(opportunity.company_logo, "https://jobboard.example/media/acme/logo.png")
        self.assertEqual(opportunity.description_html, "<h3>Missions</h3><ul><li>Develop APIs</li></ul>")
        self.assertEqual(opportunity.extra_data["procedure"], "Appel d'offres ouvert")

    def test_materialization_uses_default_logo_for_anonymous_company(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

        opportunity = materialize_opportunity(
            {
                "raw_id": 10001,
                "source": source,
                "titre": "Technicien Qualite",
                "description": "Description suffisamment longue pour garder une offre anonyme sans logo incorrect.",
                "organisation_nom": "Entreprise Anonyme",
                "company_logo": "https://www.keejob.com/media/recruiter/recruiter_73/logo.png",
                "ville": "Tunis",
                "source_item_url": "https://www.keejob.com/offres-emploi/10001/technicien-qualite",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today(),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "skills": [],
                "languages": [],
                "languages_fallback": [],
            }
        )

        self.assertEqual(opportunity.company_logo, DEFAULT_COMPANY_LOGO_URL)

    def test_materialization_does_not_fake_missing_organization(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        opportunity = materialize_opportunity(
            {
                "raw_id": 1001,
                "source": source,
                "titre": "Support Analyst",
                "description": "Description suffisamment longue pour garder la fiche exploitable sans organisation.",
                "organisation_nom": "",
                "ville": "Tunis",
                "source_item_url": "https://jobboard.example/opportunity/no-org",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today(),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "skills": [],
                "languages": [],
                "languages_fallback": [],
            }
        )

        self.assertEqual(opportunity.organisation_nom, "")

    def test_materialization_merges_structured_fields_into_extra_data_without_overwriting(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        opportunity = materialize_opportunity(
            {
                "raw_id": 1002,
                "source": source,
                "titre": "Finance Analyst",
                "description": "Description suffisamment longue avec des missions de finance et reporting.",
                "organisation_nom": "Acme",
                "ville": "Tunis",
                "source_item_url": "https://jobboard.example/opportunity/structured-extra",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today(),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "extra_data": {"company_sector": "Existing sector"},
                "job_qualifications": "Bac+5 finance",
                "company_sector": "Incoming sector",
                "company_size": "51-200",
                "reference": "REF-123",
                "experience": "2 ans",
                "contract_types": ["CDI"],
                "education_levels": ["Bac+5"],
                "skills": [],
                "languages": [],
                "languages_fallback": [],
            }
        )

        self.assertEqual(opportunity.extra_data["company_sector"], "Existing sector")
        self.assertEqual(opportunity.extra_data["company_size"], "51-200")
        self.assertEqual(opportunity.extra_data["job_qualifications"], "Bac+5 finance")
        self.assertEqual(opportunity.extra_data["contract_types"], ["CDI"])

    def test_materialization_clears_job_skills_for_projects(self):
        source = SourceOpportunite.objects.create(
            nom="MarchesPublics",
            url="https://www.marchespublics.gov.tn",
            type_source="PORTAIL_PROJET",
        )

        opportunity = materialize_opportunity(
            {
                "raw_id": 1003,
                "source": source,
                "titre": "Acquisition de materiel",
                "description": "Acquisition de materiel pour une administration publique avec cahier des charges.",
                "organisation_nom": "Municipalite Tunis",
                "ville": "Tunis",
                "source_item_url": "https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-1003",
                "type_opportunite": TypeOpportunite.PROJET,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today(),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "extra_data": {"procedure": "Appel d'offres ouvert", "lots": [{"lot": "Lot 1"}]},
                "skills": ["python", "sql"],
                "languages": [],
                "languages_fallback": [],
            }
        )

        self.assertEqual(opportunity.skills, [])

    def test_materialization_updates_existing_by_source_item_url_only(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        opportunity = Opportunite.objects.create(
            titre="Magasinier",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise A",
            ville="Tunis",
            source_item_url="https://jobboard.example/opportunity/42",
            external_id="",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 2001,
            "source": source,
            "titre": "Magasinier",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec un détail métier utile.",
            "description_html": "<p>description detaillee</p>",
            "organisation_nom": "Entreprise B",
            "company_logo": "https://jobboard.example/media/logo-b.png",
            "ville": "Sfax",
            "source_item_url": "https://jobboard.example/opportunity/42",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.EXPIREE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": date.today() - timedelta(days=1),
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)
        self.assertEqual(updated.pk, opportunity.pk)
        self.assertEqual(updated.company_logo, "https://jobboard.example/media/logo-b.png")
        self.assertEqual(updated.description_html, "<p>description detaillee</p>")
        self.assertEqual(updated.statut, StatutOpportunite.EXPIREE)
        self.assertTrue(updated.external_id)

    def test_materialization_keejob_can_correct_expired_status_to_active(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

        opportunity = Opportunite.objects.create(
            titre="Support Client",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise E",
            ville="Tunis",
            source_item_url="https://www.keejob.com/offres-emploi/123/support-client",
            external_id="",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.EXPIREE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 2004,
            "source": source,
            "titre": "Support Client",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec details utiles et contexte métier.",
            "description_html": "<p>description detaillee</p>",
            "organisation_nom": "Entreprise E",
            "company_logo": "",
            "ville": "Tunis",
            "source_item_url": "https://www.keejob.com/offres-emploi/123/support-client",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)
        self.assertEqual(updated.pk, opportunity.pk)
        self.assertEqual(updated.statut, StatutOpportunite.ACTIVE)

    def test_materialization_matches_existing_with_canonicalized_url(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        existing = Opportunite.objects.create(
            titre="Comptable",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise C",
            company_logo="https://jobboard.example/media/old-logo.png",
            ville="Tunis",
            source_item_url="https://jobboard.example/opportunity/99",
            external_id="",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 2002,
            "source": source,
            "titre": "Comptable",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec des details utiles.",
            "description_html": "<p>description detaillee</p>",
            "organisation_nom": "Entreprise C",
            "company_logo": "https://jobboard.example/media/new-logo.png",
            "ville": "Tunis",
            "source_item_url": "https://jobboard.example/opportunity/99/?utm_source=email",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)
        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.company_logo, "https://jobboard.example/media/new-logo.png")
        self.assertEqual(updated.source_item_url, "https://jobboard.example/opportunity/99")

    def test_materialization_merges_republished_offer_by_republication_key(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )
        base_description = (
            "Cabinet d'expertise comptable recrute un auditeur comptable junior pour participer "
            "aux missions d'audit legal et contractuel, verifier les comptes et rediger des rapports. "
            "Le candidat participera aux travaux de controle, a la verification des pieces comptables, "
            "a l'analyse des risques et a la preparation des syntheses pour les clients du cabinet. "
            "Cette introduction longue reste stable entre deux republications du meme poste. "
            "Les responsabilites incluent la revue des dossiers, la coordination avec les clients, "
            "la preparation des documents de mission et le suivi des recommandations internes."
        )

        first = materialize_opportunity(
            {
                "raw_id": 3001,
                "source": source,
                "titre": "Auditeurs comptable",
                "description": (
                    "Notre cabinet d'expertise comptable, reconnu pour son engagement envers "
                    "l'excellence et la qualite, cherche a renforcer son equipe en integrant "
                    "un Auditeur Comptable Junior. Le poste couvre les missions d'audit legal, "
                    "l'analyse des comptes, l'evaluation des risques et la redaction de rapports."
                ),
                "organisation_nom": "RAYON CONSULT",
                "ville": "Tunis",
                "source_item_url": "https://www.keejob.com/offres-emploi/239399/auditeurs-comptable",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today() - timedelta(days=30),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "skills": [],
                "languages": [],
                "languages_fallback": [],
            }
        )

        second = materialize_opportunity(
            {
                "raw_id": 3002,
                "source": source,
                "titre": "Auditeurs comptable",
                "description": base_description,
                "description_html": "<p>description enrichie</p>",
                "organisation_nom": "RAYON CONSULT",
                "ville": "Tunis",
                "source_item_url": "https://www.keejob.com/offres-emploi/240916/auditeurs-comptable",
                "type_opportunite": TypeOpportunite.EMPLOI,
                "statut": StatutOpportunite.ACTIVE,
                "date_publication": date.today(),
                "date_confidence": "EXACT",
                "date_limite": None,
                "organisation": None,
                "skills": ["Audit légal", "Audit contractuel", "Excel"],
                "languages": [],
                "languages_fallback": [],
            }
        )

        first.refresh_from_db()
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(Opportunite.objects.filter(source=source).count(), 1)
        self.assertEqual(first.source_item_url, "https://www.keejob.com/offres-emploi/240916/auditeurs-comptable")
        self.assertEqual(first.skills, ["Audit légal", "Audit contractuel", "Excel"])
        self.assertTrue(first.content_fingerprint)

    def test_materialization_does_not_merge_republication_with_generic_organization(self):
        source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

        common_payload = {
            "source": source,
            "titre": "Comptable",
            "organisation_nom": "Entreprise Anonyme",
            "ville": "Tunis",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        first = materialize_opportunity(
            {
                **common_payload,
                "raw_id": 3003,
                "description": "Premiere offre comptable avec organisation non exploitable.",
                "source_item_url": "https://www.keejob.com/offres-emploi/3003/comptable",
            }
        )
        second = materialize_opportunity(
            {
                **common_payload,
                "raw_id": 3004,
                "description": "Deuxieme offre comptable distincte avec organisation non exploitable.",
                "source_item_url": "https://www.keejob.com/offres-emploi/3004/comptable",
            }
        )

        self.assertNotEqual(second.pk, first.pk)
        self.assertEqual(Opportunite.objects.filter(source=source).count(), 2)

    def test_materialization_replaces_missing_incoming_logo_with_default(self):
        source = SourceOpportunite.objects.create(
            nom="JobBoard",
            url="https://jobboard.example",
            type_source="SITE_EMPLOI",
        )

        existing = Opportunite.objects.create(
            titre="Assistant RH",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise D",
            company_logo="https://jobboard.example/media/logo-rh.png",
            ville="Tunis",
            source_item_url="https://jobboard.example/opportunity/120",
            external_id="",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 2003,
            "source": source,
            "titre": "Assistant RH",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec un meilleur contexte.",
            "description_html": "",
            "organisation_nom": "Entreprise D",
            "company_logo": "",
            "ville": "Tunis",
            "source_item_url": "https://jobboard.example/opportunity/120",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)
        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.company_logo, DEFAULT_COMPANY_LOGO_URL)

    def test_materialization_can_correct_existing_experience_bounds_and_salary(self):
        source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        existing = Opportunite.objects.create(
            titre="Ingénieur Cybersécurité",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise X",
            ville="Tunisie",
            source_item_url="https://www.emploitunisie.com/offre-emploi-tunisie/ingenieur-cybersecurite-tunisie-378131",
            external_id="",
            contract_type="Freelance",
            salary="2000 - 2500 TND",
            experience_years=10,
            experience_min=10,
            experience_max=10,
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 3001,
            "source": source,
            "titre": "Ingénieur Cybersécurité",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec détails à jour.",
            "description_html": "",
            "organisation_nom": "Entreprise X",
            "company_logo": "",
            "ville": "Tunisie",
            "source_item_url": "https://www.emploitunisie.com/offre-emploi-tunisie/ingenieur-cybersecurite-tunisie-378131",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "Freelance",
            "education_level": "",
            "availability": "",
            "salary": "1800 - 2400 TND",
            "experience_years": 2,
            "experience_min": 2,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)

        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.salary, "1800 - 2400 TND")
        self.assertEqual(updated.experience_min, 2)
        self.assertIsNone(updated.experience_max)
        self.assertEqual(updated.experience_years, 2)

    def test_materialization_can_correct_city_for_same_url(self):
        source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        existing = Opportunite.objects.create(
            titre="Délégué(e) Médical - Tunis",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Laboratoire Z",
            ville="Ben Arous",
            source_item_url="https://www.emploitunisie.com/offre-emploi-tunisie/deleguee-medical-tunis-371248",
            external_id="",
            contract_type="CDI",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 3002,
            "source": source,
            "titre": "Délégué(e) Médical - Tunis",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec détails à jour.",
            "description_html": "",
            "organisation_nom": "Laboratoire Z",
            "company_logo": "",
            "ville": "Tunis",
            "source_item_url": "https://www.emploitunisie.com/offre-emploi-tunisie/deleguee-medical-tunis-371248",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "CDI",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": [],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)

        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.ville, "Tunis")

    def test_materialization_skills_merge_dedupes_case_variants(self):
        source = SourceOpportunite.objects.create(
            nom="EmploiTunisie",
            url="https://www.emploitunisie.com",
            type_source="SITE_EMPLOI",
        )

        existing = Opportunite.objects.create(
            titre="Ingénieur Cybersécurité",
            description="Description initiale suffisamment longue pour respecter la quality gate.",
            organisation_nom="Entreprise X",
            ville="Tunisie",
            source_item_url="https://www.emploitunisie.com/offre-emploi-tunisie/ingenieur-cybersecurite-tunisie-378131",
            external_id="",
            contract_type="Freelance",
            skills=["aws", "AZURE"],
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=source,
        )

        normalized_data = {
            "raw_id": 3003,
            "source": source,
            "titre": "Ingénieur Cybersécurité",
            "description": "Description enrichie suffisamment longue pour passer la quality gate avec détails à jour.",
            "description_html": "",
            "organisation_nom": "Entreprise X",
            "company_logo": "",
            "ville": "Tunisie",
            "source_item_url": "https://www.emploitunisie.com/offre-emploi-tunisie/ingenieur-cybersecurite-tunisie-378131",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "date_confidence": "EXACT",
            "date_limite": None,
            "organisation": None,
            "contract_type": "Freelance",
            "education_level": "",
            "availability": "",
            "salary": "",
            "experience_years": None,
            "experience_min": None,
            "experience_max": None,
            "skills": ["AWS", "azure", "kali linux"],
            "languages": [],
            "languages_fallback": [],
        }

        updated = materialize_opportunity(normalized_data)

        self.assertEqual(updated.pk, existing.pk)
        self.assertEqual(updated.skills, ["aws", "AZURE", "kali linux"])


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

    def test_detail_hides_organisation_and_exposes_enrichment_fields(self):
        opportunity = self.create_opp(
            statut=StatutOpportunite.EXPIREE,
            source_item_url="https://example.org/opportunity-detail",
            company_logo="https://example.org/logo.png",
            description_html="<h3>Missions</h3><ul><li>Build APIs</li></ul>",
            contract_type="CDI",
            education_level="Bac + 3",
            availability="Plein temps",
            salary="1500 TND",
            experience_min=2,
            experience_max=5,
            experience_years=2,
            skills=["python", "sql"],
            languages=["français"],
            languages_fallback=["anglais"],
            extra_data={"procedure": "Appel d'offres ouvert", "lots": [{"lot": "Lot 1"}]},
        )

        response = self.client.get(f"{self.base_url}{opportunity.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("organisation", response.data)
        self.assertEqual(response.data["contract_type"], "CDI")
        self.assertEqual(response.data["education_level"], "Bac + 3")
        self.assertEqual(response.data["availability"], "Plein temps")
        self.assertEqual(response.data["salary"], "1500 TND")
        self.assertEqual(response.data["experience"], {"min": 2, "max": 5})
        self.assertEqual(response.data["skills"], ["python", "sql"])
        self.assertEqual(response.data["languages"], ["français"])
        self.assertEqual(response.data["languages_fallback"], ["anglais"])
        self.assertEqual(response.data["source_item_url"], "https://example.org/opportunity-detail")
        self.assertEqual(response.data["company_logo"], "https://example.org/logo.png")
        self.assertEqual(response.data["description_html"], "<h3>Missions</h3><ul><li>Build APIs</li></ul>")
        self.assertEqual(response.data["extra_data"]["procedure"], "Appel d'offres ouvert")

    def test_pipeline_metrics_expose_summary_quality_and_monitoring_fields(self):
        now_value = timezone.now()
        self.create_opp(
            titre="Complete Opportunity",
            salary="1500 TND",
            skills=["python"],
            embedding_vector=[1.0, 0.0, 0.0],
        )
        self.create_opp(titre="Sparse Opportunity")
        raw_obj = RawOpportunite.objects.create(
            source=self.source,
            raw_payload={"title": "Complete Opportunity"},
            raw_titre="Complete Opportunity",
            raw_description="Raw description",
            processing_status=RawOpportuniteProcessingStatus.MATERIALIZED,
            payload_hash="metrics-raw",
        )
        RawOpportunite.objects.filter(pk=raw_obj.pk).update(
            last_seen_at=now_value,
            processed_at=now_value + timedelta(seconds=30),
        )
        PipelineRun.objects.create(
            source="jobboard",
            status=PipelineRunStatus.SUCCESS,
            started_at=now_value,
            finished_at=now_value + timedelta(seconds=60),
            duration_seconds=60.0,
            total_processed=10,
            total_created=3,
            total_updated=7,
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/metrics/pipeline/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_run_processed"], 10)
        self.assertEqual(response.data["last_run_created"], 3)
        self.assertEqual(response.data["last_run_updated"], 7)
        self.assertEqual(response.data["last_run_duration"], 60.0)
        self.assertEqual(response.data["last_run_status"], PipelineRunStatus.SUCCESS)
        self.assertEqual(response.data["pipeline_flow"]["label"], "Scraping -> Processing -> Materialization -> Embeddings")
        self.assertEqual(response.data["data_quality"]["description"], 100)
        self.assertEqual(response.data["data_quality"]["salary"], 50)
        self.assertEqual(response.data["data_quality"]["skills"], 50)
        self.assertEqual(response.data["data_quality"]["embeddings"], 50)
        self.assertEqual(response.data["pipeline_throughput"], 10.0)
        self.assertEqual(response.data["freshness_delay"], 30.0)
        self.assertIn("jobboard", response.data["source_reliability_score"])

    def test_city_filter_normalizes_query_variant(self):
        self.create_opp(titre="Tunis Opp", ville="Tunis")
        self.create_opp(titre="Sfax Opp", ville="Sfax")

        response = self.client.get(self.base_url, {"ville": "La Marsa, Tunis"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Tunis Opp", titles)
        self.assertNotIn("Sfax Opp", titles)

    def test_city_alias_filter_normalizes_query_variant(self):
        self.create_opp(titre="Tunis Opp", ville="Tunis")
        self.create_opp(titre="Sfax Opp", ville="Sfax")

        response = self.client.get(self.base_url, {"city": "La Marsa, Tunis"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Tunis Opp", titles)
        self.assertNotIn("Sfax Opp", titles)

    def test_type_alias_filter_matches_type_opportunite(self):
        self.create_opp(titre="Job Opp", type_opportunite=TypeOpportunite.EMPLOI)
        self.create_opp(titre="Stage Opp", type_opportunite=TypeOpportunite.STAGE)

        response = self.client.get(self.base_url, {"type": TypeOpportunite.STAGE})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Stage Opp", titles)
        self.assertNotIn("Job Opp", titles)

    def test_min_salary_filter_matches_numeric_threshold(self):
        self.create_opp(titre="Junior Opp", salary="900 TND")
        self.create_opp(titre="Mid Opp", salary="1 500 TND")
        self.create_opp(titre="Senior Opp", salary="2300")

        response = self.client.get(self.base_url, {"min_salary": "1200"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {item["titre"] for item in response.data["results"]}
        self.assertIn("Mid Opp", titles)
        self.assertIn("Senior Opp", titles)
        self.assertNotIn("Junior Opp", titles)

    def test_detail_experience_falls_back_to_legacy_years(self):
        opportunity = self.create_opp(
            statut=StatutOpportunite.ACTIVE,
            source_item_url="https://example.org/opportunity-legacy-experience",
            experience_years=2,
            experience_min=None,
            experience_max=None,
        )

        response = self.client.get(f"{self.base_url}{opportunity.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["experience"], {"min": 2, "max": 2})

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

    def test_stage_list_prioritizes_keejob(self):
        other_stage_source = SourceOpportunite.objects.create(
            nom="OtherStageSource",
            url="https://example.com/stages",
            type_source="SITE_STAGE",
        )
        keejob_source = SourceOpportunite.objects.create(
            nom="Keejob",
            url="https://www.keejob.com",
            type_source="SITE_EMPLOI",
        )

        other_stage = self.create_opp(
            titre="Other Source Stage",
            type_opportunite=TypeOpportunite.STAGE,
            source=other_stage_source,
            quality_score=0.80,
            date_publication=date.today(),
        )
        keejob_stage = self.create_opp(
            titre="Keejob Stage",
            type_opportunite=TypeOpportunite.STAGE,
            source=keejob_source,
            quality_score=0.90,
            date_publication=date.today(),
        )

        for param_name in ("type_opportunite", "type"):
            with self.subTest(param_name=param_name):
                response = self.client.get(self.base_url, {param_name: TypeOpportunite.STAGE})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                returned_ids = [item["id"] for item in response.data["results"]]
                self.assertIn(other_stage.pk, returned_ids)
                self.assertIn(keejob_stage.pk, returned_ids)
                self.assertEqual(returned_ids[0], keejob_stage.pk)

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

    def test_default_list_prioritizes_quality_score(self):
        lower_quality_recent = self.create_opp(
            titre="Lower Quality Recent",
            description="Short description",
            quality_score=0.70,
            date_publication=date.today(),
        )
        medium_quality_complete = self.create_opp(
            titre="Medium Quality Complete",
            description="Detailed role description",
            description_html="<p>Detailed role description</p>",
            organisation_nom="Acme",
            company_logo="https://example.com/logo.png",
            ville="Tunis",
            salary="1800 TND",
            contract_type="CDI",
            education_level="Bac + 3",
            availability="Remote",
            skills=["python", "django"],
            languages=["français"],
            normalized_industries=["software"],
            source_item_url="https://example.com/complete",
            quality_score=0.80,
            date_publication=date.today() - timedelta(days=2),
        )
        highest_quality = self.create_opp(
            titre="Highest Quality",
            description="Sparse but high quality",
            quality_score=0.95,
            date_publication=date.today() - timedelta(days=5),
        )

        response = self.client.get(self.base_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [item["id"] for item in response.data["results"]]
        self.assertLess(returned_ids.index(highest_quality.pk), returned_ids.index(medium_quality_complete.pk))
        self.assertLess(returned_ids.index(medium_quality_complete.pk), returned_ids.index(lower_quality_recent.pk))

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
        self.assertEqual(stats["created"], 2)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(stats["skipped"], 0)

        self.assertEqual(RawOpportunite.objects.count(), 2)
        raw_records = list(RawOpportunite.objects.order_by("id"))
        self.assertEqual(raw_records[0].raw_description, "Version 1")
        self.assertEqual(raw_records[1].raw_description, "Version 2")
        self.assertEqual(raw_records[0].processing_status, RawOpportuniteProcessingStatus.NEW)
        self.assertEqual(raw_records[1].processing_status, RawOpportuniteProcessingStatus.NEW)
        self.assertEqual(Opportunite.objects.count(), 0)

    def test_pipeline_updates_existing_raw_record_when_source_record_id_repeats_with_new_url(self):
        class DuplicateSourceRecordScraper(BaseOpportunityScraper):
            source_name = "LinkedIn"
            source_url = "https://www.linkedin.com/jobs/"
            source_type = "SITE_EMPLOI"

            def fetch_raw_records(self):
                return [
                    {
                        "title": "Data Engineer",
                        "description": "Version 1",
                        "organization": "Company A",
                        "opportunity_type": "job",
                        "status": "active",
                        "publication_date": "2026-03-10",
                        "source_record_id": "job-123",
                        "source_item_url": "https://www.linkedin.com/jobs/view/job-123-a",
                    },
                    {
                        "title": "Data Engineer",
                        "description": "Version 2",
                        "organization": "Company A",
                        "opportunity_type": "job",
                        "status": "active",
                        "publication_date": "2026-03-10",
                        "source_record_id": "job-123",
                        "source_item_url": "https://www.linkedin.com/jobs/view/job-123-b?utm_source=newsletter&ref=feed",
                    },
                ]

        stats = run_collection(DuplicateSourceRecordScraper())

        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["skipped"], 0)
        self.assertEqual(RawOpportunite.objects.count(), 1)
        raw_record = RawOpportunite.objects.get()
        self.assertEqual(raw_record.source_record_id, "job-123")
        self.assertEqual(raw_record.source_item_url, "https://www.linkedin.com/jobs/view/job-123-b")
        self.assertEqual(raw_record.raw_description, "Version 2")

    def test_pipeline_updates_existing_raw_record_by_url_when_record_id_changes(self):
        class DuplicateUrlScraper(BaseOpportunityScraper):
            source_name = "LinkedIn"
            source_url = "https://www.linkedin.com/jobs/"
            source_type = "SITE_EMPLOI"

            def fetch_raw_records(self):
                return [
                    {
                        "title": "ML Engineer",
                        "description": "Version 1",
                        "organization": "Company A",
                        "status": "active",
                        "publication_date": "2026-03-10",
                        "source_record_id": "job-a",
                        "source_item_url": "https://www.linkedin.com/jobs/view/job-shared?utm_campaign=old",
                    },
                    {
                        "title": "ML Engineer",
                        "description": "Version 2",
                        "organization": "Company A",
                        "status": "active",
                        "publication_date": "2026-03-10",
                        "source_record_id": "job-b",
                        "source_item_url": "https://www.linkedin.com/jobs/view/job-shared?utm_campaign=new",
                    },
                ]

        stats = run_collection(DuplicateUrlScraper())

        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["skipped"], 0)
        self.assertEqual(RawOpportunite.objects.count(), 1)
        raw_record = RawOpportunite.objects.get()
        self.assertEqual(raw_record.source_record_id, "job-b")
        self.assertEqual(raw_record.source_item_url, "https://www.linkedin.com/jobs/view/job-shared")
        self.assertEqual(raw_record.raw_description, "Version 2")

    def test_pipeline_recovers_when_concurrent_insert_wins_race(self):
        source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://www.linkedin.com/jobs/",
            type_source="SITE_EMPLOI",
        )
        RawOpportunite.objects.create(
            source=source,
            raw_payload={"title": "Race"},
            raw_titre="Race",
            raw_description="Before",
            source_record_id="race-1",
            source_item_url="https://www.linkedin.com/jobs/view/race-1",
            payload_hash="existing-race-hash",
            content_fingerprint="race-fingerprint",
        )

        raw_record = {
            "title": "Race",
            "description": "After",
            "organization": "Company A",
            "status": "active",
            "publication_date": "2026-03-10",
            "source_record_id": "race-1",
            "source_item_url": "https://www.linkedin.com/jobs/view/race-1?utm_medium=email",
        }

        with patch(
            "opportunities.scraping.pipeline._upsert_raw_opportunity_by_identity",
            side_effect=IntegrityError("duplicate key"),
        ):
            raw_opportunity, created, _ = scraping_pipeline._shadow_store_raw_record(
                raw_record,
                source,
                payload_hash="race-hash",
                content_fingerprint="race-fingerprint-new",
            )

        self.assertFalse(created)
        self.assertEqual(RawOpportunite.objects.count(), 1)
        self.assertEqual(raw_opportunity.raw_description, "After")
        self.assertEqual(raw_opportunity.payload_hash, "race-hash")

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
        self.assertEqual(stats["created"], 1)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(stats["skipped"], 0)
        self.assertEqual(RawOpportunite.objects.count(), 1)
        self.assertEqual(Opportunite.objects.count(), 0)
