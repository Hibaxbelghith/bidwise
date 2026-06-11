from concurrent.futures import ThreadPoolExecutor

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from users.models import ProfileResume, Utilisateur

from .models import Candidature, StatutSuiviCandidature


@override_settings(PROFILE_RESUME_USE_CLOUDINARY=False)
class OrganizationRejectApplicationEndpointTests(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.organization = Utilisateur.objects.create_user(
            username="reject-app-organization",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.other_organization = Utilisateur.objects.create_user(
            username="reject-app-other-organization",
            email="other-organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.candidate = Utilisateur.objects.create_user(
            username="reject-app-candidate",
            email="candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.other_candidate = Utilisateur.objects.create_user(
            username="reject-app-other-candidate",
            email="other-candidate@example.com",
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
        self.other_opportunity = self._create_opportunity(
            "Frontend Developer",
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
        candidate=None,
        cv=None,
        cover_letter_url="",
    ):
        return Candidature.objects.create(
            candidat=candidate or self.candidate,
            opportunite=opportunity or self.opportunity,
            statut=application_status,
            submitted_at=timezone.now(),
            cv=cv,
            cover_letter_url=cover_letter_url,
        )

    @staticmethod
    def _url(opportunity_id, application_id):
        return (
            f"/api/organization/opportunities/{opportunity_id}/"
            f"applications/{application_id}/reject/"
        )

    def _reject(self, application, *, opportunity=None):
        self.client.force_authenticate(self.organization)
        return self.client.patch(
            self._url(
                (opportunity or self.opportunity).pk,
                application.pk,
            ),
            {},
            format="json",
        )

    def test_submitted_application_can_be_rejected(self):
        application = self._create_application()

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["application_id"], application.pk)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.REJECTED)

    def test_viewed_application_can_be_rejected(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
        )

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.REJECTED)

    def test_shortlisted_application_can_be_rejected(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.SHORTLISTED,
        )

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], StatutSuiviCandidature.REJECTED)

    def test_rejected_application_is_idempotent(self):
        application = self._create_application(
            application_status=StatutSuiviCandidature.REJECTED,
        )

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["detail"],
            "Application rejected successfully.",
        )
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.REJECTED)

    def test_non_rejectable_statuses_return_conflict(self):
        self.client.force_authenticate(self.organization)
        blocked_statuses = [
            StatutSuiviCandidature.WITHDRAWN,
            StatutSuiviCandidature.VUE,
            StatutSuiviCandidature.INTERESSEE,
            StatutSuiviCandidature.POSTULEE_EXTERNEMENT,
            StatutSuiviCandidature.ABANDONNEE,
        ]

        for blocked_status in blocked_statuses:
            with self.subTest(application_status=blocked_status):
                application = self._create_application(
                    application_status=blocked_status,
                )

                response = self.client.patch(
                    self._url(self.opportunity.pk, application.pk),
                    {},
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
                application.refresh_from_db()
                self.assertEqual(application.statut, blocked_status)
                application.delete()

    def test_other_organization_opportunity_returns_not_found(self):
        application = self._create_application(
            opportunity=self.foreign_opportunity,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.foreign_opportunity.pk, application.pk),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_application_from_another_opportunity_returns_not_found(self):
        application = self._create_application(
            opportunity=self.other_opportunity,
        )

        response = self._reject(application, opportunity=self.opportunity)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_application_returns_not_found(self):
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(self.opportunity.pk, 999999),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unknown_opportunity_returns_not_found(self):
        application = self._create_application()
        self.client.force_authenticate(self.organization)

        response = self.client.patch(
            self._url(999999, application.pk),
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

    def test_rejection_is_persisted_in_database(self):
        application = self._create_application()

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.REJECTED)

    def test_rejection_preserves_cv_and_cover_letter(self):
        resume = ProfileResume.objects.create(
            profile=self.candidate.profil,
            file=SimpleUploadedFile(
                "resume.pdf",
                b"%PDF-1.4 candidate resume",
                content_type="application/pdf",
            ),
            is_active=True,
        )
        cover_letter_url = "https://example.com/cover-letter.pdf"
        application = self._create_application(
            cv=resume,
            cover_letter_url=cover_letter_url,
        )

        response = self._reject(application)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.cv_id, resume.pk)
        self.assertEqual(application.cover_letter_url, cover_letter_url)

    def test_concurrent_rejections_leave_consistent_state(self):
        application = self._create_application()
        url = self._url(self.opportunity.pk, application.pk)

        def reject_once():
            close_old_connections()
            client = APIClient()
            client.force_authenticate(self.organization)
            try:
                return client.patch(url, {}, format="json").status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            status_codes = list(executor.map(lambda _: reject_once(), range(2)))

        self.assertEqual(
            sorted(status_codes),
            [status.HTTP_200_OK, status.HTTP_200_OK],
        )
        application.refresh_from_db()
        self.assertEqual(application.statut, StatutSuiviCandidature.REJECTED)
