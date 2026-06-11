from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from users.models import Utilisateur

from .models import Candidature, StatutSuiviCandidature


class ExternalApplicationStatusUpdateEndpointTests(APITestCase):
    def setUp(self):
        self.candidate = Utilisateur.objects.create_user(
            username="external-status-candidate",
            email="candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.other_candidate = Utilisateur.objects.create_user(
            username="external-status-other-candidate",
            email="other@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.organization = Utilisateur.objects.create_user(
            username="external-status-organization",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://linkedin.com",
            type_source="SITE_EMPLOI",
        )
        self.opportunity = Opportunite.objects.create(
            titre="Sales Executive",
            organisation_nom="Acme Tunisia",
            ville="Tunis",
            description="Grow enterprise accounts in Tunisia.",
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=self.source,
            source_item_url="https://linkedin.com/jobs/view/456",
        )

    def _create_application(self, *, candidate=None, application_status=None):
        return Candidature.objects.create(
            candidat=candidate or self.candidate,
            opportunite=self.opportunity,
            statut=application_status or StatutSuiviCandidature.EXTERNAL_CLICKED,
            url_source=self.opportunity.source_item_url,
            submitted_at=timezone.now(),
        )

    @staticmethod
    def _url(application):
        return f"/api/me/applications/{application.pk}/external-status/"

    def test_candidate_can_confirm_external_application(self):
        application = self._create_application()
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)

    def test_candidate_can_mark_remind_later(self):
        application = self._create_application()
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_REMIND_LATER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_REMIND_LATER)

    def test_confirm_is_idempotent(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)

    def test_remind_later_is_idempotent(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_REMIND_LATER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.EXTERNAL_REMIND_LATER)

    def test_candidate_can_confirm_after_remind_later(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)

    def test_confirmed_application_cannot_move_back_to_remind_later(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_REMIND_LATER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)

    def test_legacy_external_status_can_be_confirmed(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED)

    def test_internal_workflow_application_returns_conflict(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.SUBMITTED,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_invalid_status_is_rejected(self):
        application = self._create_application()
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": "WITHDRAWN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_candidate_application_returns_not_found(self):
        application = self._create_application(candidate=self.other_candidate)
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organization_account_is_forbidden(self):
        application = self._create_application()
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        application = self._create_application()

        response = self.client.patch(
            self._url(application),
            {"status": StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
