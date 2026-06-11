from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from users.models import Utilisateur

from .models import Candidature, StatutSuiviCandidature


class CandidateApplicationListEndpointTests(APITestCase):
    url = "/api/me/applications/"

    def setUp(self):
        self.candidate = Utilisateur.objects.create_user(
            username="candidate-applications",
            email="candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.other_candidate = Utilisateur.objects.create_user(
            username="other-candidate-applications",
            email="other@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.organization = Utilisateur.objects.create_user(
            username="organization-applications",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.newer_opportunity = Opportunite.objects.create(
            titre="Backend Developer",
            organisation_nom="Acme Tunisia",
            ville="Tunis",
            description="Build reliable backend services.",
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=source,
            organisation=self.organization,
        )
        self.older_opportunity = Opportunite.objects.create(
            titre="Frontend Developer",
            organisation_nom="Acme Tunisia",
            ville="Sousse",
            description="Build accessible user interfaces.",
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=source,
            organisation=self.organization,
        )

    def test_candidate_receives_only_own_applications_in_submission_order(self):
        now = timezone.now()
        older = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.older_opportunity,
            statut=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            submitted_at=now - timedelta(days=1),
        )
        newer = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.newer_opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=now,
            cover_letter_url="https://example.com/cover-letter.pdf",
        )
        Candidature.objects.create(
            candidat=self.other_candidate,
            opportunite=self.newer_opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=now + timedelta(minutes=1),
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [newer.pk, older.pk],
        )
        self.assertEqual(
            set(response.data[0]),
            {
                "id",
                "opportunity_id",
                "opportunity_title",
                "organisation_name",
                "ville",
                "statut",
                "submitted_at",
                "cover_letter_url",
            },
        )
        self.assertEqual(response.data[0]["opportunity_id"], self.newer_opportunity.pk)
        self.assertEqual(response.data[0]["opportunity_title"], "Backend Developer")
        self.assertEqual(response.data[0]["organisation_name"], "Acme Tunisia")
        self.assertEqual(response.data[0]["ville"], "Tunis")

    def test_external_clicked_tracking_is_hidden_from_candidate_dashboard(self):
        now = timezone.now()
        hidden_tracking = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.older_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_CLICKED,
        )
        submitted = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.newer_opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=now,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [submitted.pk])
        self.assertTrue(Candidature.objects.filter(pk=hidden_tracking.pk).exists())

    def test_confirmed_and_reminder_external_applications_are_visible(self):
        now = timezone.now()
        remind_later = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.older_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_REMIND_LATER,
            submitted_at=now - timedelta(hours=1),
        )
        confirmed = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.newer_opportunity,
            statut=StatutSuiviCandidature.EXTERNAL_APPLIED_CONFIRMED,
            submitted_at=now,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [confirmed.pk, remind_later.pk],
        )

    def test_organization_account_is_forbidden(self):
        self.client.force_authenticate(self.organization)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CandidateApplicationWithdrawEndpointTests(APITestCase):
    def setUp(self):
        self.candidate = Utilisateur.objects.create_user(
            username="withdraw-candidate",
            email="withdraw@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.other_candidate = Utilisateur.objects.create_user(
            username="withdraw-other-candidate",
            email="withdraw-other@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.organization = Utilisateur.objects.create_user(
            username="withdraw-organization",
            email="withdraw-organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.opportunity = Opportunite.objects.create(
            titre="Data Analyst",
            organisation_nom="Acme Tunisia",
            ville="Tunis",
            description="Analyze operational data and produce reports.",
            statut=StatutOpportunite.ACTIVE,
            date_publication=timezone.localdate(),
            source=source,
            organisation=self.organization,
        )

    def _create_application(self, *, candidate=None, application_status=None):
        return Candidature.objects.create(
            candidat=candidate or self.candidate,
            opportunite=self.opportunity,
            statut=application_status or StatutSuiviCandidature.SUBMITTED,
            submitted_at=timezone.now(),
        )

    @staticmethod
    def _url(application):
        return f"/api/me/applications/{application.pk}/withdraw/"

    def test_owner_can_withdraw_submitted_application(self):
        application = self._create_application()
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.WITHDRAWN)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.WITHDRAWN)

    def test_owner_can_withdraw_viewed_application(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.WITHDRAWN)

    def test_owner_can_withdraw_shortlisted_application(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.SHORTLISTED,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.WITHDRAWN)

    def test_withdrawn_application_is_idempotent(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.WITHDRAWN,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.WITHDRAWN)

    def test_non_withdrawable_statuses_return_conflict(self):
        self.client.force_authenticate(self.candidate)

        blocked_statuses = [
            StatutSuiviCandidature.VUE,
            StatutSuiviCandidature.INTERESSEE,
            StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
            StatutSuiviCandidature.ABANDONNEE,
            StatutSuiviCandidature.REJECTED,
        ]
        for blocked_status in blocked_statuses:
            with self.subTest(application_status=blocked_status):
                application = self._create_application(
                    application_status=blocked_status,
                )

                response = self.client.patch(
                    self._url(application),
                    {},
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
                application.refresh_from_db()
                self.assertEqual(application.statut, blocked_status)
                application.delete()

    def test_application_owned_by_another_candidate_returns_not_found(self):
        application = self._create_application(candidate=self.other_candidate)
        self.client.force_authenticate(self.candidate)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.SUBMITTED)

    def test_organization_account_is_forbidden(self):
        application = self._create_application()
        self.client.force_authenticate(self.organization)

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        application = self._create_application()

        response = self.client.patch(self._url(application), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
