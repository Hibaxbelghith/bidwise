from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import (
    Opportunite,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from users.models import Utilisateur

from .models import Candidature, StatutSuiviCandidature


class ExternalApplyClickEndpointTests(APITestCase):
    def setUp(self):
        self.candidate = Utilisateur.objects.create_user(
            username="external-candidate",
            email="external-candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.other_candidate = Utilisateur.objects.create_user(
            username="external-other-candidate",
            email="external-other@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.organization = Utilisateur.objects.create_user(
            username="external-organization",
            email="external-organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.external_source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://linkedin.com",
            type_source="SITE_EMPLOI",
        )
        self.organization_source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.external_opportunity = Opportunite.objects.create(
            titre="Customer Success Specialist",
            description="Support customers across the MENA region.",
            organisation_nom="Acme Tunisia",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=self.external_source,
            source_item_url="https://linkedin.com/jobs/view/123",
        )
        self.organization_opportunity = Opportunite.objects.create(
            titre="Backend Developer",
            description="Build and maintain Django APIs.",
            organisation_nom="BidWise",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=self.organization_source,
            organisation=self.organization,
        )

    def _url(self, opportunity):
        return f"/api/opportunities/{opportunity.pk}/external-apply-click/"

    def test_candidate_can_start_external_tracking(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = Candidature.objects.get(pk=response.data["application_id"])
        self.assertEqual(application.candidat, self.candidate)
        self.assertEqual(application.opportunite, self.external_opportunity)
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_CLICKED)
        self.assertEqual(application.url_source, self.external_opportunity.source_item_url)
        self.assertEqual(application.contact_email, self.candidate.email)
        self.assertIsNotNone(application.submitted_at)

    def test_existing_clicked_tracking_is_idempotent(self):
        application = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.external_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_CLICKED,
            url_source="https://linkedin.com/jobs/view/old",
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_CLICKED)
        self.assertEqual(application.url_source, self.external_opportunity.source_item_url)

    def test_confirmed_external_application_is_not_downgraded(self):
        application = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.external_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
            url_source="https://linkedin.com/jobs/view/old",
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)
        self.assertEqual(application.url_source, self.external_opportunity.source_item_url)

    def test_legacy_external_status_is_upgraded_to_external_clicked(self):
        application = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.external_opportunity,
            statut=StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_CLICKED)

    def test_internal_application_conflicts_with_external_tracking(self):
        Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.external_opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_organization_owned_opportunity_is_rejected(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.organization_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_opportunity_without_external_link_is_rejected(self):
        self.external_opportunity.source_item_url = ""
        self.external_opportunity.save(update_fields=["source_item_url"])
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_opportunity_is_rejected(self):
        self.external_opportunity.statut = StatutOpportunite.EXPIREE
        self.external_opportunity.save(update_fields=["statut"])
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_organization_account_is_forbidden(self):
        self.client.force_authenticate(self.organization)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_candidate_tracking_does_not_block_owner(self):
        Candidature.objects.create(
            candidat=self.other_candidate,
            opportunite=self.external_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_CLICKED,
            submitted_at=timezone.now(),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self._url(self.external_opportunity), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
