from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
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
from opportunities.tasks import send_organization_admin_decision_email_task
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
    def test_organization_can_partially_update_own_opportunity(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.94,
            reason="The updated content describes a legitimate professional role.",
            provider="gemini",
            model="gemini-test",
        )
        opportunity = self.create_opportunity(
            owner=self.organization,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "category": CATEGORY_UNCLEAR,
                        "decision": DECISION_PENDING_REVIEW,
                        "confidence": 0.6,
                        "reason": "Previous content required review.",
                    },
                    "final_decision": DECISION_PENDING_REVIEW,
                    "final_status": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {
                "title": "Senior Java Developer",
                "experience_min": 5,
                "experience_max": 8,
                "skills": ["Java", "Spring", "Java"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.titre, "Senior Java Developer")
        self.assertEqual(opportunity.description, "Build and maintain internal applications.")
        self.assertEqual(opportunity.experience_min, 5)
        self.assertEqual(opportunity.experience_max, 8)
        self.assertEqual(opportunity.skills, ["Java", "Spring"])
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)
        moderation = opportunity.extra_data["moderation"]
        self.assertEqual(moderation["final_decision"], DECISION_APPROVED)
        self.assertEqual(len(moderation["history"]), 1)
        self.assertEqual(
            moderation["last_update"]["changed_fields"],
            ["experience_max", "experience_min", "skills", "title"],
        )
        audit = AuditLog.objects.get(
            action=AuditLog.Action.UPDATE_ORG_OPPORTUNITY,
            metadata__opportunity_id=opportunity.id,
        )
        self.assertEqual(audit.metadata["ai_category"], CATEGORY_LEGITIMATE)
        self.assertEqual(audit.metadata["after_status"], StatutOpportunite.ACTIVE)
        self.assertIn("title", audit.metadata["changed_fields"])

    def test_organization_can_retrieve_complete_own_opportunity(self):
        project_details = {
            "public_buyer": "Municipality of Test",
            "region_execution": "Tunis",
            "procedure": "Appel d'offres ouvert",
            "deadline_time": "10:00",
            "lots": [{"lot": "Lot 1", "objet": "IT equipment", "quantite": "1"}],
            "documents": [
                {
                    "type": "cahier_des_charges",
                    "url": "https://example.com/specifications.pdf",
                    "label": "Cahier des charges",
                }
            ],
        }
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Acquisition of IT equipment",
            description="Complete public tender description for professional IT equipment.",
            type_opportunite=TypeOpportunite.PROJET,
            extra_data={"published_by": "organization", "project_details": project_details},
        )
        self.client.force_authenticate(self.organization)

        response = self.client.get(f"{self.url}{opportunity.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], opportunity.description)
        self.assertEqual(response.data["project_details"]["public_buyer"], "Municipality of Test")
        self.assertEqual(len(response.data["project_details"]["lots"]), 1)
        self.assertEqual(len(response.data["project_details"]["documents"]), 1)
        self.assertIn("internship_details", response.data)
        self.assertIn("seasonal_details", response.data)

    def test_organization_cannot_retrieve_another_organizations_opportunity(self):
        opportunity = self.create_opportunity(owner=self.other_organization)
        self.client.force_authenticate(self.organization)

        response = self.client.get(f"{self.url}{opportunity.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_update_revalidates_complete_opportunity(self):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"experience_min": 10},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("experience_max", response.data)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.experience_min, 2)
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)

    def test_organization_cannot_update_another_organizations_opportunity(self):
        opportunity = self.create_opportunity(owner=self.other_organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Unauthorized title change"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.titre, "Junior Java Developer")

    def test_candidate_cannot_update_organization_opportunity(self):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Unauthorized title change"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_rejects_immutable_and_unknown_fields(self):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {
                "type": TypeOpportunite.STAGE,
                "status": StatutOpportunite.ACTIVE,
                "extra_data": {"moderation": {}},
                "unexpected": "value",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("immutable_fields", response.data)
        self.assertIn("unknown_fields", response.data)

    def test_closed_archived_or_expired_opportunity_cannot_be_updated(self):
        closed = self.create_opportunity(
            owner=self.organization,
            title="Closed opportunity",
            statut=StatutOpportunite.FERMEE,
        )
        archived = self.create_opportunity(
            owner=self.organization,
            title="Archived opportunity",
            statut=StatutOpportunite.ARCHIVEE,
        )
        expired = self.create_opportunity(
            owner=self.organization,
            title="Expired opportunity",
            statut=StatutOpportunite.EXPIREE,
        )
        self.client.force_authenticate(self.organization)

        closed_response = self.client.patch(
            f"{self.url}{closed.id}/",
            {"title": "Updated closed opportunity"},
            format="json",
        )
        archived_response = self.client.patch(
            f"{self.url}{archived.id}/",
            {"title": "Updated archived opportunity"},
            format="json",
        )
        expired_response = self.client.patch(
            f"{self.url}{expired.id}/",
            {"title": "Updated expired opportunity"},
            format="json",
        )

        self.assertEqual(closed_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(archived_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(expired_response.status_code, status.HTTP_409_CONFLICT)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_suspended_opportunity_can_be_updated_without_becoming_public(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.95,
            reason="The updated content describes a legitimate professional role.",
            provider="gemini",
            model="gemini-test",
        )
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Suspended role",
            statut=StatutOpportunite.SUSPENDUE,
            extra_data={
                "published_by": "organization",
                "organization_status": {
                    "suspended_from": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Updated suspended role"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.SUSPENDUE)
        self.assertEqual(
            opportunity.extra_data["organization_status"]["suspended_from"],
            StatutOpportunite.ACTIVE,
        )
        self.assertEqual(
            opportunity.extra_data["moderation"]["activation_status"],
            StatutOpportunite.ACTIVE,
        )

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_rejected_opportunity_update_always_requires_admin_review(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.99,
            reason="The corrected content describes a legitimate professional role.",
            provider="gemini",
            model="gemini-test",
        )
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Rejected role",
            statut=StatutOpportunite.REJECTED,
            extra_data={"published_by": "organization"},
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Corrected rejected role"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(
            opportunity.extra_data["moderation"]["llm"]["decision"],
            DECISION_APPROVED,
        )
        self.assertTrue(
            opportunity.extra_data["moderation"]["last_update"]["requires_admin_review"],
        )
        audit = AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE_ORG_OPPORTUNITY,
            metadata__opportunity_id=opportunity.id,
        ).latest("created_at")
        self.assertEqual(audit.metadata["before_status"], StatutOpportunite.REJECTED)
        self.assertEqual(audit.metadata["after_status"], StatutOpportunite.PENDING_REVIEW)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_partial_update_preserves_internship_details(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.92,
            reason="The content describes a legitimate internship.",
            provider="gemini",
            model="gemini-test",
        )
        start_date = (date.today() + timedelta(days=20)).isoformat()
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Data Internship",
            type_opportunite=TypeOpportunite.STAGE,
            contract_type="Internship",
            experience_min=None,
            experience_max=None,
            extra_data={
                "published_by": "organization",
                "internship_details": {
                    "internship_type": "GRADUATION_PROJECT",
                    "duration": "4_6_MONTHS",
                    "start_date": start_date,
                },
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"description": "Join our data team for a supervised graduation internship using Python and SQL."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(
            opportunity.extra_data["internship_details"]["internship_type"],
            "GRADUATION_PROJECT",
        )
        self.assertEqual(opportunity.contract_type, "Internship")

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_partial_update_preserves_seasonal_details(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.9,
            reason="The content describes a legitimate seasonal role.",
            provider="gemini",
            model="gemini-test",
        )
        start_date = (date.today() + timedelta(days=20)).isoformat()
        end_date = (date.today() + timedelta(days=80)).isoformat()
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Summer Assistant",
            type_opportunite=TypeOpportunite.SAISONNIER,
            contract_type="Seasonal",
            experience_min=None,
            experience_max=None,
            extra_data={
                "published_by": "organization",
                "seasonal_details": {
                    "season": "SUMMER",
                    "start_date": start_date,
                    "end_date": end_date,
                },
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"salary": "950 TND"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.salary, "950 TND")
        self.assertEqual(opportunity.extra_data["seasonal_details"]["season"], "SUMMER")

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_partial_update_preserves_tender_documents_and_lots(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.91,
            reason="The content describes a legitimate public tender.",
            provider="gemini",
            model="gemini-test",
        )
        deadline = date.today() + timedelta(days=30)
        project_details = {
            "public_buyer": "Municipality of Test",
            "region_execution": "Tunis",
            "procedure": "Appel d'offres ouvert",
            "deadline_time": "10:00",
            "number_of_lots": "1",
            "lots": [
                {
                    "lot": "Lot 1",
                    "objet": "IT equipment",
                    "quantite": "1",
                    "region": "Tunis",
                    "caution": "1000 TND",
                }
            ],
            "documents": [
                {
                    "type": "cahier_des_charges",
                    "url": "https://example.com/specifications.pdf",
                    "label": "Cahier des charges",
                }
            ],
        }
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Acquisition of IT equipment",
            type_opportunite=TypeOpportunite.PROJET,
            contract_type="",
            availability="",
            experience_min=None,
            experience_max=None,
            education_level="",
            skills=[],
            date_limite=deadline,
            extra_data={
                "published_by": "organization",
                "project_details": project_details,
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"description": "Open public tender for the acquisition and delivery of professional IT equipment."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        details = opportunity.extra_data["project_details"]
        self.assertEqual(details["public_buyer"], "Municipality of Test")
        self.assertEqual(len(details["lots"]), 1)
        self.assertEqual(len(details["documents"]), 1)
        self.assertEqual(opportunity.organisation_nom, "Municipality of Test")

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_suspicious_update_remains_pending_review(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_SCAM,
            decision=DECISION_REJECTED,
            confidence=1.0,
            reason="The candidate is asked to pay a registration fee.",
            provider="gemini",
            model="gemini-test",
        )
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {
                "description": (
                    "Remote assistant role. Candidates must pay a registration fee "
                    "before receiving access to the work platform."
                )
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(opportunity.extra_data["moderation"]["final_decision"], DECISION_REJECTED)

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_update_llm_failure_falls_back_to_pending_review(self, mock_moderation):
        mock_moderation.side_effect = Exception("Gemini timeout")
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Updated Java Developer"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(
            opportunity.extra_data["moderation"]["final_decision"],
            DECISION_PENDING_REVIEW,
        )

    @override_settings(TURNSTILE_SECRET_KEY="test-secret")
    def test_update_requires_turnstile_token_when_configured(self):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": "Updated Java Developer"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("turnstile_token", response.data)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.titre, "Junior Java Developer")

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_identical_update_is_idempotent_and_skips_moderation(self, mock_moderation):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {"title": opportunity.titre},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "No changes were needed.")
        self.assertEqual(response.data["opportunity"]["id"], opportunity.id)
        mock_moderation.assert_not_called()

    def test_organization_can_suspend_and_activate_active_opportunity(self):
        opportunity = self.create_opportunity(owner=self.organization)
        self.client.force_authenticate(self.organization)

        suspend_response = self.client.post(
            f"{self.url}{opportunity.id}/suspend/",
            format="json",
        )
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.SUSPENDUE)

        activate_response = self.client.post(
            f"{self.url}{opportunity.id}/activate/",
            format="json",
        )
        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.ACTIVE)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.SUSPEND_ORG_OPPORTUNITY,
                metadata__opportunity_id=opportunity.id,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.Action.ACTIVATE_ORG_OPPORTUNITY,
                metadata__opportunity_id=opportunity.id,
            ).exists()
        )

    def test_pending_opportunity_returns_to_pending_after_suspension(self):
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Pending opportunity",
            statut=StatutOpportunite.PENDING_REVIEW,
        )
        self.client.force_authenticate(self.organization)

        suspend_response = self.client.post(
            f"{self.url}{opportunity.id}/suspend/",
            format="json",
        )
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(suspend_response.data["opportunity"]["status"], StatutOpportunite.SUSPENDUE)
        self.assertEqual(
            suspend_response.data["opportunity"]["suspended_from"],
            StatutOpportunite.PENDING_REVIEW,
        )

        activate_response = self.client.post(
            f"{self.url}{opportunity.id}/activate/",
            format="json",
        )
        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(
            activate_response.data["opportunity"]["status"],
            StatutOpportunite.PENDING_REVIEW,
        )

    def test_closed_opportunity_can_be_reopened_without_bypassing_review(self):
        self.client.force_authenticate(self.organization)
        active = self.create_opportunity(
            owner=self.organization,
            title="Active opportunity to reopen",
            statut=StatutOpportunite.ACTIVE,
        )
        pending = self.create_opportunity(
            owner=self.organization,
            title="Pending opportunity to reopen",
            statut=StatutOpportunite.PENDING_REVIEW,
        )

        for opportunity, expected_status in (
            (active, StatutOpportunite.ACTIVE),
            (pending, StatutOpportunite.PENDING_REVIEW),
        ):
            close_response = self.client.post(
                f"{self.url}{opportunity.id}/close/",
                format="json",
            )
            self.assertEqual(close_response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                close_response.data["opportunity"]["closed_from"],
                opportunity.statut,
            )

            activate_response = self.client.post(
                f"{self.url}{opportunity.id}/activate/",
                format="json",
            )
            self.assertEqual(activate_response.status_code, status.HTTP_200_OK)
            opportunity.refresh_from_db()
            self.assertEqual(opportunity.statut, expected_status)

    def test_closed_opportunity_can_be_suspended(self):
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Closed opportunity to suspend",
            statut=StatutOpportunite.ACTIVE,
        )
        self.client.force_authenticate(self.organization)

        self.client.post(f"{self.url}{opportunity.id}/close/", format="json")
        suspend_response = self.client.post(
            f"{self.url}{opportunity.id}/suspend/",
            format="json",
        )

        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            suspend_response.data["opportunity"]["status"],
            StatutOpportunite.SUSPENDUE,
        )
        self.assertEqual(
            suspend_response.data["opportunity"]["suspended_from"],
            StatutOpportunite.ACTIVE,
        )

    def test_pending_origin_survives_suspend_close_activate_chain(self):
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Pending chained status opportunity",
            statut=StatutOpportunite.PENDING_REVIEW,
        )
        self.client.force_authenticate(self.organization)

        suspend_response = self.client.post(
            f"{self.url}{opportunity.id}/suspend/",
            format="json",
        )
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            suspend_response.data["opportunity"]["suspended_from"],
            StatutOpportunite.PENDING_REVIEW,
        )

        close_response = self.client.post(
            f"{self.url}{opportunity.id}/close/",
            format="json",
        )
        self.assertEqual(close_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            close_response.data["opportunity"]["closed_from"],
            StatutOpportunite.PENDING_REVIEW,
        )

        activate_response = self.client.post(
            f"{self.url}{opportunity.id}/activate/",
            format="json",
        )
        self.assertEqual(activate_response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.statut, StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(
            activate_response.data["opportunity"]["status"],
            StatutOpportunite.PENDING_REVIEW,
        )

    def test_close_accepts_all_organization_closable_statuses(self):
        self.client.force_authenticate(self.organization)
        for index, initial_status in enumerate(
            [
                StatutOpportunite.ACTIVE,
                StatutOpportunite.SUSPENDUE,
                StatutOpportunite.PENDING_REVIEW,
                StatutOpportunite.REJECTED,
            ]
        ):
            opportunity = self.create_opportunity(
                owner=self.organization,
                title=f"Closable opportunity {index}",
                statut=initial_status,
            )
            response = self.client.post(
                f"{self.url}{opportunity.id}/close/",
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            opportunity.refresh_from_db()
            self.assertEqual(opportunity.statut, StatutOpportunite.FERMEE)

            repeated_response = self.client.post(
                f"{self.url}{opportunity.id}/close/",
                format="json",
            )
            self.assertEqual(repeated_response.status_code, status.HTTP_200_OK)

    def test_status_actions_reject_invalid_transitions_and_other_owner(self):
        pending = self.create_opportunity(
            owner=self.organization,
            title="Pending opportunity",
            statut=StatutOpportunite.PENDING_REVIEW,
        )
        archived = self.create_opportunity(
            owner=self.organization,
            title="Archived opportunity status",
            statut=StatutOpportunite.ARCHIVEE,
        )
        other = self.create_opportunity(owner=self.other_organization)
        self.client.force_authenticate(self.organization)

        self.assertEqual(
            self.client.post(f"{self.url}{pending.id}/suspend/").status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(f"{self.url}{archived.id}/close/").status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            self.client.post(f"{self.url}{other.id}/close/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_suspended_and_closed_opportunities_are_hidden_from_public_detail(self):
        suspended = self.create_opportunity(
            owner=self.organization,
            title="Suspended opportunity",
            statut=StatutOpportunite.SUSPENDUE,
        )
        closed = self.create_opportunity(
            owner=self.organization,
            title="Closed opportunity",
            statut=StatutOpportunite.FERMEE,
        )

        self.client.force_authenticate(user=None)
        suspended_response = self.client.get(f"/api/opportunities/{suspended.id}/")
        closed_response = self.client.get(f"/api/opportunities/{closed.id}/")

        self.assertEqual(suspended_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(closed_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_tender_create_rejects_negative_quantity_and_past_dates(self):
        self.client.force_authenticate(self.organization)
        past_date = (date.today() - timedelta(days=1)).isoformat()
        deadline = (date.today() + timedelta(days=20)).isoformat()
        payload = self.valid_post_payload(
            title="Acquisition of office equipment",
            type=TypeOpportunite.PROJET,
            deadline=deadline,
            project_details={
                "public_buyer": "Municipality of Test",
                "region_execution": "Tunis",
                "procedure": "Appel d'offres ouvert",
                "deadline_time": "10:00",
                "execution_start_date": past_date,
                "opening_date": past_date,
                "lots": [
                    {
                        "lot": "Lot 1",
                        "objet": "Office equipment",
                        "quantite": "-2",
                        "region": "Tunis",
                        "caution": "1000 TND",
                    }
                ],
            },
        )

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_details", response.data)

    def test_tender_update_rejects_negative_quantity_and_past_dates(self):
        deadline = date.today() + timedelta(days=30)
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Acquisition of equipment",
            type_opportunite=TypeOpportunite.PROJET,
            date_limite=deadline,
            extra_data={
                "published_by": "organization",
                "project_details": {
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Tunis",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "lots": [
                        {
                            "lot": "Lot 1",
                            "objet": "Equipment",
                            "quantite": "1",
                            "region": "Tunis",
                            "caution": "1000 TND",
                        }
                    ],
                    "documents": [],
                },
            },
        )
        self.client.force_authenticate(self.organization)
        past_date = (date.today() - timedelta(days=1)).isoformat()

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {
                "project_details": {
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Tunis",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "execution_start_date": past_date,
                    "lots": [
                        {
                            "lot": "Lot 1",
                            "objet": "Equipment",
                            "quantite": "-2",
                            "region": "Tunis",
                            "caution": "1000 TND",
                        }
                    ],
                    "documents": [],
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_details", response.data)
        opportunity.refresh_from_db()
        self.assertEqual(
            opportunity.extra_data["project_details"]["lots"][0]["quantite"],
            "1",
        )

    @patch("opportunities.views.classify_opportunity_with_gemini")
    def test_tender_update_replaces_document_url(self, mock_moderation):
        mock_moderation.return_value = ModerationLLMResult(
            category=CATEGORY_LEGITIMATE,
            decision=DECISION_APPROVED,
            confidence=0.93,
            reason="The updated tender remains legitimate.",
            provider="gemini",
            model="gemini-test",
        )
        deadline = date.today() + timedelta(days=30)
        old_url = "https://example.com/old-notice.pdf"
        new_url = "https://example.com/new-notice.pdf"
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Acquisition of equipment",
            type_opportunite=TypeOpportunite.PROJET,
            date_limite=deadline,
            extra_data={
                "published_by": "organization",
                "project_details": {
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Tunis",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "documents": [
                        {
                            "type": "avis_appel_offres",
                            "url": old_url,
                            "label": "Old notice",
                        }
                    ],
                    "lots": [],
                },
            },
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            f"{self.url}{opportunity.id}/",
            {
                "project_details": {
                    "public_buyer": "Municipality of Test",
                    "region_execution": "Tunis",
                    "procedure": "Appel d'offres ouvert",
                    "deadline_time": "10:00",
                    "documents": [
                        {
                            "type": "avis_appel_offres",
                            "url": new_url,
                            "label": "New notice",
                        }
                    ],
                    "lots": [],
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity.refresh_from_db()
        documents = opportunity.extra_data["project_details"]["documents"]
        self.assertEqual(documents[0]["url"], new_url)
        self.assertNotEqual(documents[0]["url"], old_url)

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

    @patch("opportunities.views_admin.send_organization_admin_decision_email_task.delay")
    def test_admin_can_approve_pending_organization_opportunity(self, mock_email_delay):
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

        with self.captureOnCommitCallbacks(execute=True):
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
        mock_email_delay.assert_called_once()
        self.assertEqual(mock_email_delay.call_args.args[:2], (pending.id, "approved"))

    @patch("opportunities.views_admin.send_organization_admin_decision_email_task.delay")
    def test_admin_can_reject_pending_organization_opportunity(self, mock_email_delay):
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

        with self.captureOnCommitCallbacks(execute=True):
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
        mock_email_delay.assert_called_once()
        self.assertEqual(mock_email_delay.call_args.args[:2], (pending.id, "rejected"))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="BidWise <test@bidwise.com>",
        BIDWISE_FRONTEND_URL="http://localhost:5173",
        BIDWISE_SUPPORT_EMAIL="support@bidwise.test",
    )
    def test_rejection_email_uses_admin_note_and_never_exposes_llm_reason(self):
        decision_id = "2026-06-08T12:00:00+00:00"
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Suspicious remote role",
            statut=StatutOpportunite.REJECTED,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "category": CATEGORY_SCAM,
                        "reason": "TECHNICAL LLM REASON MUST NEVER BE EXPOSED",
                    },
                    "admin_decision": {
                        "action": "rejected",
                        "note": "Please remove the payment request and submit again.",
                        "decided_at": decision_id,
                    },
                },
            },
        )

        result = send_organization_admin_decision_email_task.apply(
            args=[opportunity.id, "rejected", decision_id],
        ).get()

        self.assertEqual(result["status"], "sent")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Please remove the payment request", message.body)
        self.assertNotIn("TECHNICAL LLM REASON", message.body)
        self.assertNotIn("TECHNICAL LLM REASON", message.alternatives[0][0])
        opportunity.refresh_from_db()
        notification = opportunity.extra_data["moderation"]["admin_decision"]["email_notification"]
        self.assertEqual(notification["status"], "sent")
        self.assertEqual(notification["recipient"], "org@example.com")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="BidWise <test@bidwise.com>",
        BIDWISE_FRONTEND_URL="http://localhost:5173",
    )
    def test_approval_email_is_idempotent_for_the_same_admin_decision(self):
        decision_id = "2026-06-08T12:30:00+00:00"
        opportunity = self.create_opportunity(
            owner=self.organization,
            title="Backend Developer",
            statut=StatutOpportunite.ACTIVE,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "admin_decision": {
                        "action": "approved",
                        "note": "",
                        "decided_at": decision_id,
                    },
                },
            },
        )

        first = send_organization_admin_decision_email_task.apply(
            args=[opportunity.id, "approved", decision_id],
        ).get()
        second = send_organization_admin_decision_email_task.apply(
            args=[opportunity.id, "approved", decision_id],
        ).get()

        self.assertEqual(first["status"], "sent")
        self.assertEqual(second, {"status": "skipped", "reason": "already_sent"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            f"http://localhost:5173/opportunities/{opportunity.id}",
            mail.outbox[0].body,
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
