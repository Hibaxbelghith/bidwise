from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from applications.models import Candidature
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.moderation_llm import (
    CATEGORY_LEGITIMATE,
    CATEGORY_SCAM,
    CATEGORY_UNCLEAR,
    DECISION_APPROVED,
    DECISION_PENDING_REVIEW,
    DECISION_REJECTED,
    ModerationLLMResult,
)
from users.models import AuditLog, OrganizationProfile, Utilisateur


@override_settings(GEMINI_API_KEY="", GEMINI_FALLBACK_MODELS="", TURNSTILE_SECRET_KEY="")
class OrganizationOpportunitiesAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("organization_opportunities")
        self.document_upload_url = reverse("organization_tender_document_upload")
        self.source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.organization = Utilisateur.objects.create_user(
            username="org-owner",
            email="org@example.com",
            password="test-password",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.other_organization = Utilisateur.objects.create_user(
            username="other-org",
            email="other-org@example.com",
            password="test-password",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.candidate = Utilisateur.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="test-password",
        )
        self.admin = Utilisateur.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="test-password",
            is_admin=True,
            is_staff=True,
        )
        OrganizationProfile.objects.create(
            user=self.organization,
            organization_name="Acme Tunisia",
            first_name="Lina",
            last_name="Mansour",
            phone="+21612345678",
            organization_type=OrganizationProfile.OrganizationType.COMPANY,
        )
        OrganizationProfile.objects.create(
            user=self.other_organization,
            organization_name="Other Tunisia",
            first_name="Nour",
            last_name="Ben Ali",
            phone="+21687654321",
            organization_type=OrganizationProfile.OrganizationType.COMPANY,
        )

    def create_opportunity(self, *, owner, title="Junior Java Developer", **overrides):
        payload = {
            "titre": title,
            "description": "Build and maintain internal applications.",
            "organisation_nom": "Acme Tunisia",
            "ville": "Tunis",
            "contract_type": "CDI",
            "availability": "Full time",
            "experience_min": 2,
            "experience_max": 5,
            "education_level": "Bac+5",
            "salary": "",
            "skills": ["Java", "SQL"],
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": date.today(),
            "organisation": owner,
            "source": self.source,
        }
        payload.update(overrides)
        return Opportunite.objects.create(**payload)

    def valid_post_payload(self, **overrides):
        payload = {
            "title": "Junior Java Developer",
            "type": TypeOpportunite.EMPLOI,
            "location": "Tunis",
            "description": (
                "We are looking for a junior Java developer to build internal "
                "business applications and collaborate with product teams."
            ),
            "contract": "CDI",
            "availability": "Full time",
            "experience_min": 2,
            "experience_max": 5,
            "education_level": "Bac+5",
            "salary": "",
            "skills": ["Java", "SQL", "java", ""],
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
        }
        payload.update(overrides)
        return payload

    def test_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_candidate_receives_forbidden(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Organization account required.")

    def test_organization_without_profile_receives_forbidden(self):
        user = Utilisateur.objects.create_user(
            username="org-no-profile",
            email="org-no-profile@example.com",
            password="test-password",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("organization profile", response.data["detail"])

    def test_organization_sees_only_own_opportunities(self):
        own = self.create_opportunity(owner=self.organization)
        self.create_opportunity(owner=self.other_organization, title="Other organization role")
        self.create_opportunity(owner=None, title="External scraped role")
        Candidature.objects.create(candidat=self.candidate, opportunite=own)
        self.client.force_authenticate(self.organization)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["id"], own.id)
        self.assertEqual(item["title"], "Junior Java Developer")
        self.assertEqual(item["type"], TypeOpportunite.EMPLOI)
        self.assertEqual(item["status"], StatutOpportunite.ACTIVE)
        self.assertEqual(item["location"], "Tunis")
        self.assertEqual(item["contract"], "CDI")
        self.assertEqual(item["experience_min"], 2)
        self.assertEqual(item["experience_max"], 5)
        self.assertEqual(item["skills"], ["Java", "SQL"])
        self.assertEqual(item["applications_count"], 1)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_organization_can_create_opportunity(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.92,
            reason="The offer describes a real professional role.",
            provider="gemini",
            model="gemini-test",
        )
        self.client.force_authenticate(self.organization)

        response = self.client.post(self.url, self.valid_post_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.organisation, self.organization)
        self.assertEqual(opportunity.organisation_nom, "Acme Tunisia")
        self.assertEqual(opportunity.source.nom, "BidWise Organizations")
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(opportunity.type_opportunite, TypeOpportunite.EMPLOI)
        self.assertEqual(opportunity.date_publication, date.today())
        self.assertEqual(opportunity.titre, "Junior Java Developer")
        self.assertEqual(opportunity.ville, "Tunis")
        self.assertEqual(opportunity.extra_data["moderation"]["llm"]["category"], CATEGORY_LEGITIMATE)
        self.assertEqual(opportunity.extra_data["moderation"]["llm"]["decision"], DECISION_APPROVED)
        self.assertEqual(opportunity.extra_data["moderation"]["final_status"], StatutOpportunite.ACTIVE)
        self.assertEqual(opportunity.skills, ["Java", "SQL"])
        self.assertEqual(opportunity.raw_skills, ["Java", "SQL"])
        self.assertEqual(opportunity.normalized_contract_types, ["CDI"])
        self.assertEqual(response.data["applications_count"], 0)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_scraped_company_history_reduces_new_organization_flag(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.92,
            reason="The offer describes a real professional role.",
            provider="gemini",
            model="gemini-test",
        )
        external_source = SourceOpportunite.objects.create(
            nom="External Jobs",
            url="https://external.example.com",
            type_source="AUTRE",
        )
        self.create_opportunity(
            owner=None,
            title="Existing Acme Role",
            organisation_nom="Acme Tunisia",
            source=external_source,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.post(self.url, self.valid_post_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)
        moderation = opportunity.extra_data["moderation"]
        self.assertEqual(moderation["llm"]["decision"], DECISION_APPROVED)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_suspicious_organization_opportunity_is_pending_review(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_SCAM,
            decision=DECISION_REJECTED,
            confidence=1.0,
            reason="The candidate is asked to pay money before starting.",
            provider="gemini",
            model="gemini-test",
        )
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Remote Assistant",
                description=(
                    "Travail facile depuis chez vous, revenu garanti. "
                    "Des frais de dossier de 30 TND sont requis. "
                    "Contact WhatsApp uniquement."
                ),
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(opportunity.extra_data["moderation"]["llm"]["category"], CATEGORY_SCAM)
        self.assertEqual(opportunity.extra_data["moderation"]["llm"]["decision"], DECISION_REJECTED)
        self.assertEqual(opportunity.extra_data["moderation"]["final_status"], StatutOpportunite.PENDING_REVIEW)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_ambiguous_opportunity_uses_llm_final_decision(self, mock_judge):
        mock_judge.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.86,
            reason="The title is a false positive and the job is coherent.",
            skipped=False,
            provider="gemini",
            model="gemini-test",
        )
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(title="PFE Platform Engineer"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        moderation = opportunity.extra_data["moderation"]
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)
        self.assertFalse(moderation["llm"]["skipped"])
        self.assertEqual(moderation["llm"]["provider"], "gemini")
        self.assertEqual(moderation["final_decision"], DECISION_APPROVED)
        mock_judge.assert_called_once()

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_llm_failure_falls_back_to_pending_review(self, mock_judge):
        mock_judge.side_effect = Exception("Gemini timeout")
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(title="PFE Platform Engineer"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        moderation = opportunity.extra_data["moderation"]
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertTrue(moderation["llm"]["skipped"])
        self.assertEqual(moderation["final_decision"], DECISION_PENDING_REVIEW)
        self.assertEqual(moderation["final_status"], StatutOpportunite.PENDING_REVIEW)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_organization_can_create_internship_with_details(self, mock_judge):
        mock_judge.return_value = ModerationLLMResult(
            category=CATEGORY_UNCLEAR,
            decision=DECISION_PENDING_REVIEW,
            confidence=0.4,
            reason="Internship details need review.",
            skipped=False,
            provider="gemini",
            model="gemini-test",
        )
        self.client.force_authenticate(self.organization)
        start_date = (date.today() + timedelta(days=15)).isoformat()

        response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Data Science Internship",
                type=TypeOpportunite.STAGE,
                contract="CDI",
                experience_min=3,
                experience_max=6,
                internship_details={
                    "internship_type": "GRADUATION_PROJECT",
                    "duration": "4_6_MONTHS",
                    "start_date": start_date,
                },
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.type_opportunite, TypeOpportunite.STAGE)
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(opportunity.contract_type, "Internship")
        self.assertEqual(opportunity.normalized_contract_types, ["INTERNSHIP"])
        self.assertIsNone(opportunity.experience_min)
        self.assertIsNone(opportunity.experience_max)
        self.assertEqual(opportunity.salary, "")
        self.assertEqual(
            opportunity.extra_data["internship_details"],
            {
                "internship_type": "GRADUATION_PROJECT",
                "duration": "4_6_MONTHS",
                "start_date": start_date,
            },
        )
        moderation = opportunity.extra_data["moderation"]
        self.assertEqual(moderation["llm"]["decision"], DECISION_PENDING_REVIEW)
        self.assertEqual(response.data["internship_details"]["duration"], "4_6_MONTHS")

    def test_internship_details_are_required_only_for_internships(self):
        self.client.force_authenticate(self.organization)
        start_date = (date.today() + timedelta(days=15)).isoformat()

        missing_details_response = self.client.post(
            self.url,
            self.valid_post_payload(type=TypeOpportunite.STAGE),
            format="json",
        )
        job_with_details_response = self.client.post(
            self.url,
            self.valid_post_payload(
                internship_details={
                    "internship_type": "GRADUATION_PROJECT",
                    "duration": "4_6_MONTHS",
                    "start_date": start_date,
                },
            ),
            format="json",
        )

        self.assertEqual(missing_details_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("internship_details", missing_details_response.data)
        self.assertEqual(job_with_details_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("internship_details", job_with_details_response.data)

    def test_organization_can_create_seasonal_opportunity_with_details(self):
        self.client.force_authenticate(self.organization)
        start_date = (date.today() + timedelta(days=20)).isoformat()
        end_date = (date.today() + timedelta(days=80)).isoformat()

        response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Summer Event Assistant",
                type=TypeOpportunite.SAISONNIER,
                contract="CDD",
                experience_min=2,
                experience_max=4,
                salary="900 TND",
                seasonal_details={
                    "season": "SUMMER",
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.type_opportunite, TypeOpportunite.SAISONNIER)
        self.assertEqual(opportunity.contract_type, "Seasonal")
        self.assertEqual(opportunity.normalized_contract_types, ["SEASONAL"])
        self.assertIsNone(opportunity.experience_min)
        self.assertIsNone(opportunity.experience_max)
        self.assertEqual(opportunity.salary, "900 TND")
        self.assertEqual(
            opportunity.extra_data["seasonal_details"],
            {
                "season": "SUMMER",
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        self.assertEqual(response.data["seasonal_details"]["season"], "SUMMER")

    def test_seasonal_details_are_required_only_for_seasonal_opportunities(self):
        self.client.force_authenticate(self.organization)
        start_date = (date.today() + timedelta(days=20)).isoformat()
        end_date = (date.today() + timedelta(days=80)).isoformat()

        missing_details_response = self.client.post(
            self.url,
            self.valid_post_payload(type=TypeOpportunite.SAISONNIER),
            format="json",
        )
        job_with_details_response = self.client.post(
            self.url,
            self.valid_post_payload(
                seasonal_details={
                    "season": "SUMMER",
                    "start_date": start_date,
                    "end_date": end_date,
                },
            ),
            format="json",
        )
        invalid_range_response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Winter Activity Assistant",
                type=TypeOpportunite.SAISONNIER,
                seasonal_details={
                    "season": "WINTER",
                    "start_date": end_date,
                    "end_date": start_date,
                },
            ),
            format="json",
        )

        self.assertEqual(missing_details_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seasonal_details", missing_details_response.data)
        self.assertEqual(job_with_details_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seasonal_details", job_with_details_response.data)
        self.assertEqual(invalid_range_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seasonal_details", invalid_range_response.data)

    def test_organization_can_create_call_for_tender_with_project_details(self):
        self.client.force_authenticate(self.organization)
        deadline = (date.today() + timedelta(days=30)).isoformat()
        opening_date = (date.today() + timedelta(days=30)).isoformat()

        response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Acquisition of IT equipment",
                type=TypeOpportunite.PROJET,
                location="Ben Arous",
                deadline=deadline,
                contract="CDI",
                availability="Full time",
                salary="1200 TND",
                skills=["Java"],
                experience_min=2,
                experience_max=4,
                project_details={
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Ben Arous",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "tender_number": "Tender-100",
                    "number_of_lots": "1",
                    "lot_type": "Lot unique",
                    "price_character": "Marché à prix unitaire",
                    "delai_validite": "120",
                    "opening_date": opening_date,
                    "opening_time": "11:30",
                    "opening_address": "Ben Arous",
                    "evaluation_methodology": "Moins disant",
                    "type_commande": "Matériel",
                    "financement": "fonds propres",
                    "marche_cadre": False,
                    "marche_general": False,
                    "lots": [
                        {
                            "lot": "Lot 1",
                            "objet": "Acquisition of IT equipment",
                            "quantite": "1",
                            "region": "Ben Arous",
                            "caution": "1500 TND",
                        }
                    ],
                    "documents": [
                        {
                            "type": "cahier_des_charges",
                            "url": "https://example.com/specs.pdf",
                            "label": "Cahier des charges",
                        },
                        {
                            "type": "avis_appel_offres",
                            "url": "https://example.com/notice.pdf",
                            "label": "Avis d'appel d'offres",
                        },
                    ],
                },
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=response.data["id"])
        self.assertEqual(opportunity.type_opportunite, TypeOpportunite.PROJET)
        self.assertEqual(opportunity.organisation_nom, "Municipality of Test")
        self.assertEqual(opportunity.contract_type, "")
        self.assertEqual(opportunity.availability, "")
        self.assertEqual(opportunity.salary, "")
        self.assertEqual(opportunity.skills, [])
        self.assertIsNone(opportunity.experience_min)
        self.assertEqual(opportunity.extra_data["procedure"], "Appel d'offres ouvert")
        self.assertEqual(opportunity.extra_data["region_execution"], "Ben Arous")
        self.assertEqual(opportunity.extra_data["delai_validite"], "120")
        self.assertEqual(opportunity.extra_data["caution"], "1500 TND")
        self.assertTrue(opportunity.extra_data["has_pdf"])
        self.assertEqual(opportunity.extra_data["pdf_url"], "https://example.com/notice.pdf")
        self.assertEqual(opportunity.extra_data["cahier_des_charges_url"], "https://example.com/specs.pdf")

    def test_call_for_tender_requires_project_details_and_valid_document_urls(self):
        self.client.force_authenticate(self.organization)
        deadline = (date.today() + timedelta(days=30)).isoformat()

        missing_details_response = self.client.post(
            self.url,
            self.valid_post_payload(type=TypeOpportunite.PROJET, deadline=deadline),
            format="json",
        )
        invalid_document_response = self.client.post(
            self.url,
            self.valid_post_payload(
                title="Acquisition of services",
                type=TypeOpportunite.PROJET,
                deadline=deadline,
                project_details={
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Tunis",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "documents": [
                        {"type": "avis_appel_offres", "url": "not-a-url", "label": "Notice"}
                    ],
                },
            ),
            format="json",
        )

        self.assertEqual(missing_details_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_details", missing_details_response.data)
        self.assertEqual(invalid_document_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_details", invalid_document_response.data)

    def test_candidate_cannot_create_opportunity(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self.url, self.valid_post_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Opportunite.objects.filter(titre="Junior Java Developer").exists())

    @override_settings(TURNSTILE_SECRET_KEY="test-secret")
    def test_turnstile_token_is_required_when_configured(self):
        self.client.force_authenticate(self.organization)

        response = self.client.post(self.url, self.valid_post_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("turnstile_token", response.data)
        self.assertFalse(Opportunite.objects.filter(titre="Junior Java Developer").exists())

    @override_settings(TURNSTILE_SECRET_KEY="test-secret")
    @patch("opportunities.turnstile.requests.post")
    def test_invalid_turnstile_token_is_rejected(self, mock_post):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"success": False, "error-codes": ["invalid-input-response"]}

        mock_post.return_value = FakeResponse()
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(turnstile_token="bad-token"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("turnstile_token", response.data)
        self.assertFalse(Opportunite.objects.filter(titre="Junior Java Developer").exists())

    @override_settings(TURNSTILE_SECRET_KEY="test-secret")
    @patch("opportunities.views.classify_opportunity_with_gemini")
    @patch("opportunities.turnstile.requests.post")
    def test_valid_turnstile_token_allows_publication(self, mock_post, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.92,
            reason="The offer describes a real professional role.",
            provider="gemini",
            model="gemini-test",
        )

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"success": True}

        mock_post.return_value = FakeResponse()
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(turnstile_token="valid-token"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Opportunite.objects.filter(titre="Junior Java Developer").exists())
        mock_post.assert_called_once()

    def test_organization_without_profile_cannot_create_opportunity(self):
        user = Utilisateur.objects.create_user(
            username="org-no-profile-post",
            email="org-no-profile-post@example.com",
            password="test-password",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.client.force_authenticate(user)

        response = self.client.post(self.url, self.valid_post_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("organization profile", response.data["detail"])

    def test_create_opportunity_validates_required_fields(self):
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(title="Java", type="UNKNOWN", description="Too short."),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        self.assertIn("type", response.data)
        self.assertIn("description", response.data)

    def test_create_opportunity_validates_experience_range_and_deadline(self):
        self.client.force_authenticate(self.organization)

        range_response = self.client.post(
            self.url,
            self.valid_post_payload(
                experience_min=6,
                experience_max=2,
            ),
            format="json",
        )
        deadline_response = self.client.post(
            self.url,
            self.valid_post_payload(deadline=(date.today() - timedelta(days=1)).isoformat()),
            format="json",
        )

        self.assertEqual(range_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("experience_max", range_response.data)
        self.assertEqual(deadline_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", deadline_response.data)

    def test_create_opportunity_limits_skills(self):
        self.client.force_authenticate(self.organization)

        response = self.client.post(
            self.url,
            self.valid_post_payload(skills=[f"Skill {index}" for index in range(16)]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skills", response.data)

    def test_create_opportunity_rejects_negative_numbers(self):
        self.client.force_authenticate(self.organization)

        experience_response = self.client.post(
            self.url,
            self.valid_post_payload(experience_min=-1, experience_max=2),
            format="json",
        )
        salary_response = self.client.post(
            self.url,
            self.valid_post_payload(salary="-1000 TND"),
            format="json",
        )

        self.assertEqual(experience_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("experience_min", experience_response.data)
        self.assertEqual(salary_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("salary", salary_response.data)

    def test_create_opportunity_restricts_location_to_tunisia_list(self):
        self.client.force_authenticate(self.organization)

        invalid_response = self.client.post(
            self.url,
            self.valid_post_payload(location="Paris"),
            format="json",
        )
        canonical_response = self.client.post(
            self.url,
            self.valid_post_payload(title="Backend Engineer", location="gabes"),
            format="json",
        )

        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("location", invalid_response.data)
        self.assertEqual(canonical_response.status_code, status.HTTP_201_CREATED)
        opportunity = Opportunite.objects.get(id=canonical_response.data["id"])
        self.assertEqual(opportunity.ville, "Gabès")

    def test_organization_opportunity_post_is_rate_limited(self):
        self.client.force_authenticate(self.organization)

        responses = [
            self.client.post(
                self.url,
                self.valid_post_payload(title=f"Backend Engineer {index}"),
                format="json",
            )
            for index in range(6)
        ]

        self.assertEqual([response.status_code for response in responses[:5]], [status.HTTP_201_CREATED] * 5)
        self.assertEqual(responses[5].status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_organization_opportunity_get_is_not_rate_limited(self):
        self.client.force_authenticate(self.organization)

        for _index in range(8):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_organization_can_upload_tender_document(self):
        self.client.force_authenticate(self.organization)
        upload = SimpleUploadedFile(
            "cahier.pdf",
            b"%PDF-1.4 test tender document",
            content_type="application/pdf",
        )

        response = self.client.post(
            self.document_upload_url,
            {"file": upload, "type": "cahier_des_charges", "label": "Cahier des charges"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["type"], "cahier_des_charges")
        self.assertEqual(response.data["label"], "Cahier des charges")
        self.assertIn("url", response.data)

    def test_tender_document_upload_rejects_invalid_file_type(self):
        self.client.force_authenticate(self.organization)
        upload = SimpleUploadedFile(
            "malware.exe",
            b"not a tender document",
            content_type="application/octet-stream",
        )

        response = self.client.post(
            self.document_upload_url,
            {"file": upload, "type": "avis_appel_offres"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_admin_pending_organization_opportunities_requires_authentication(self):
        response = self.client.get("/api/admin/organization-opportunities/pending/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_pending_organization_opportunities_requires_admin(self):
        self.client.force_authenticate(self.organization)

        response = self.client.get("/api/admin/organization-opportunities/pending/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_pending_organization_opportunities(self):
        pending = self.create_opportunity(
            owner=self.organization,
            title="Pending organization role",
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "skipped": False,
                        "category": CATEGORY_SCAM,
                        "decision": DECISION_REJECTED,
                        "confidence": 0.9,
                        "reason": "The candidate is asked to pay money before starting.",
                    },
                    "final_decision": DECISION_REJECTED,
                    "final_status": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )
        self.create_opportunity(
            owner=self.organization,
            title="Active organization role",
            statut=StatutOpportunite.ACTIVE,
            extra_data={"published_by": "organization"},
        )
        self.create_opportunity(
            owner=None,
            title="Pending scraped role",
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={"published_by": "scraper"},
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get("/api/admin/organization-opportunities/pending/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(item["id"], pending.id)
        self.assertEqual(item["title"], "Pending organization role")
        self.assertEqual(item["status"], StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(item["organization_email"], "org@example.com")
        self.assertIn("moderation", item)
        self.assertEqual(item["moderation"]["llm"]["category"], CATEGORY_SCAM)
        self.assertEqual(item["moderation"]["llm"]["decision"], DECISION_REJECTED)

    def test_admin_can_approve_pending_organization_opportunity(self):
        pending = self.create_opportunity(
            owner=self.organization,
            title="Pending review role",
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "category": CATEGORY_UNCLEAR,
                        "decision": DECISION_PENDING_REVIEW,
                        "confidence": 0.5,
                        "reason": "Needs admin review.",
                    },
                    "final_decision": DECISION_PENDING_REVIEW,
                    "final_status": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/api/admin/organization-opportunities/{pending.id}/approve/",
            {"note": "Looks legitimate."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending.refresh_from_db()
        self.assertEqual(pending.statut, StatutOpportunite.ACTIVE)
        moderation = pending.extra_data["moderation"]
        self.assertEqual(moderation["admin_decision"]["action"], "approved")
        self.assertEqual(moderation["admin_decision"]["note"], "Looks legitimate.")
        self.assertEqual(moderation["final_decision"], DECISION_APPROVED)
        self.assertEqual(moderation["final_status"], StatutOpportunite.ACTIVE)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.admin,
                target=self.organization,
                action=AuditLog.Action.APPROVE_ORG_OPPORTUNITY,
                metadata__opportunity_id=pending.id,
            ).exists()
        )

    def test_admin_can_reject_pending_organization_opportunity(self):
        pending = self.create_opportunity(
            owner=self.organization,
            title="Suspicious organization role",
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "category": CATEGORY_SCAM,
                        "decision": DECISION_REJECTED,
                        "confidence": 0.95,
                        "reason": "The candidate is asked to pay money.",
                    },
                    "final_decision": DECISION_REJECTED,
                    "final_status": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/api/admin/organization-opportunities/{pending.id}/reject/",
            {"note": "Payment request detected."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pending.refresh_from_db()
        self.assertEqual(pending.statut, StatutOpportunite.REJECTED)
        moderation = pending.extra_data["moderation"]
        self.assertEqual(moderation["admin_decision"]["action"], "rejected")
        self.assertEqual(moderation["admin_decision"]["note"], "Payment request detected.")
        self.assertEqual(moderation["final_decision"], DECISION_REJECTED)
        self.assertEqual(moderation["final_status"], StatutOpportunite.REJECTED)
        self.assertTrue(
            AuditLog.objects.filter(
                actor=self.admin,
                target=self.organization,
                action=AuditLog.Action.REJECT_ORG_OPPORTUNITY,
                metadata__opportunity_id=pending.id,
            ).exists()
        )

    def test_candidate_cannot_approve_organization_opportunity(self):
        pending = self.create_opportunity(
            owner=self.organization,
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={"published_by": "organization"},
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(f"/api/admin/organization-opportunities/{pending.id}/approve/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_approve_scraped_opportunity_through_organization_endpoint(self):
        scraped = self.create_opportunity(
            owner=None,
            statut=StatutOpportunite.PENDING_REVIEW,
            extra_data={"published_by": "scraper"},
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/admin/organization-opportunities/{scraped.id}/approve/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
