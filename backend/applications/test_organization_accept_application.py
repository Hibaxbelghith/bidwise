from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from users.models import Utilisateur

from .models import Candidature, StatutSuiviCandidature


@override_settings(PROFILE_RESUME_USE_CLOUDINARY=False)
class OrganizationAcceptApplicationEndpointTests(APITestCase):
    def setUp(self):
        self.organization = Utilisateur.objects.create_user(
            username="accept-app-organization",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.other_organization = Utilisateur.objects.create_user(
            username="accept-app-other-organization",
            email="other-organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.candidate = Utilisateur.objects.create_user(
            username="accept-app-candidate",
            email="candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.opportunity = self._create_opportunity(
            "Backend Developer",
            self.organization,
            source,
        )
        self.foreign_opportunity = self._create_opportunity(
            "Data Analyst",
            self.other_organization,
            source,
        )

    @staticmethod
    def _create_opportunity(title, organization, source):
        return Opportunite.objects.create(
            titre=title,
            organisation_nom="Acme Tunisia",
            ville="Tunis",
            description="A complete professional opportunity.",
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=source,
            organisation=organization,
        )

    def _create_application(
        self,
        *,
        application_status=StatutSuiviCandidature.SUBMITTED,
        opportunity=None,
    ):
        return Candidature.objects.create(
            candidat=self.candidate,
            opportunite=opportunity or self.opportunity,
            statut=application_status,
            submitted_at=timezone.now(),
        )

    @staticmethod
    def _url(opportunity_id, application_id):
        return (
            f"/api/organization/opportunities/{opportunity_id}/"
            f"applications/{application_id}/accept/"
        )

    def test_submitted_application_can_be_shortlisted(self):
        application = self._create_application()
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.SHORTLISTED)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.SHORTLISTED)

    def test_rejected_application_can_be_shortlisted(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.REJECTED,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.SHORTLISTED)

    def test_viewed_application_can_be_shortlisted(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.SHORTLISTED)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.SHORTLISTED)

    def test_shortlisted_application_is_idempotent(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.SHORTLISTED,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.SHORTLISTED)

    def test_withdrawn_application_returns_conflict(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.WITHDRAWN,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_other_organization_opportunity_returns_not_found(self):
        application = self._create_application(opportunity=self.foreign_opportunity)
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.foreign_opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_candidate_account_is_forbidden(self):
        application = self._create_application()
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        application = self._create_application()

        response = self.client.patch(
            self._url(self.opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
