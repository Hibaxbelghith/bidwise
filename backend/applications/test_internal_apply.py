from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from opportunities.models import (
    Opportunite,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from opportunities.tasks import notify_candidate_application_submitted_task
from users.models import ProfileResume, Utilisateur

from .models import Candidature, StatutSuiviCandidature


@override_settings(PROFILE_RESUME_USE_CLOUDINARY=False)
class InternalApplicationEndpointTests(APITestCase):
    def setUp(self):
        self.candidate = Utilisateur.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.resume = ProfileResume.objects.create(
            profile=self.candidate.profil,
            file=SimpleUploadedFile(
                "resume.pdf",
                b"%PDF-1.4 candidate resume",
                content_type="application/pdf",
            ),
            is_active=True,
        )
        self.organization = Utilisateur.objects.create_user(
            username="organization",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.organization_source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.external_source = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://linkedin.com",
            type_source="SITE_EMPLOI",
        )
        self.opportunity = Opportunite.objects.create(
            titre="Backend Developer",
            description="Build and maintain reliable Django services.",
            organisation_nom="Acme Tunisia",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication="2026-06-09",
            source=self.organization_source,
            organisation=self.organization,
        )
        self.apply_url = f"/api/opportunities/{self.opportunity.pk}/apply/"

    def _payload(self, **overrides):
        payload = {
            "cv_id": self.resume.pk,
            "contact_email": "candidate@example.com",
            "contact_phone": "+21612345678",
        }
        payload.update(overrides)
        return payload

    def test_candidate_can_submit_application(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = Candidature.objects.get(pk=response.data["application_id"])
        self.assertEqual(application.statut, StatutSuiviCandidature.SUBMITTED)
        self.assertEqual(application.cv, self.resume)
        self.assertEqual(application.contact_email, "candidate@example.com")
        self.assertEqual(application.contact_phone, "+21612345678")
        self.assertIsNotNone(application.submitted_at)

    @patch("applications.views.notify_candidate_application_submitted_task.delay")
    @patch("applications.views.notify_organization_new_application_task.delay")
    def test_submission_dispatches_candidate_and_organization_notifications(
        self,
        mock_org_delay,
        mock_candidate_delay,
    ):
        self.client.force_authenticate(self.candidate)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application_id = response.data["application_id"]
        mock_org_delay.assert_called_once_with(application_id=application_id)
        mock_candidate_delay.assert_called_once_with(application_id=application_id)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_candidate_submission_email_task_sends_email(self):
        application = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            cv=self.resume,
            contact_email="candidate@example.com",
            submitted_at=timezone.now(),
        )

        result = notify_candidate_application_submitted_task.apply(
            kwargs={"application_id": application.pk}
        )

        self.assertEqual(result.result["status"], "sent")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["candidate@example.com"])
        self.assertIn("Application submitted", message.subject)
        self.assertIn("Backend Developer", message.body)

    def test_cover_letter_upload_accepts_pdf(self):
        self.client.force_authenticate(self.candidate)
        upload = SimpleUploadedFile(
            "cover-letter.pdf",
            b"%PDF-1.4 cover letter",
            content_type="application/pdf",
        )

        response = self.client.post(
            "/api/applications/cover-letter-upload/",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(f"/application_cover_letters/{self.candidate.pk}/", response.data["url"])

    def test_non_active_opportunity_is_rejected(self):
        self.client.force_authenticate(self.candidate)
        self.opportunity.statut = StatutOpportunite.SUSPENDUE
        self.opportunity.save(update_fields=["statut"])

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_external_source_is_rejected(self):
        self.client.force_authenticate(self.candidate)
        self.opportunity.source = self.external_source
        self.opportunity.organisation = None
        self.opportunity.save(update_fields=["source", "organisation"])

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tender_is_rejected(self):
        self.client.force_authenticate(self.candidate)
        self.opportunity.type_opportunite = TypeOpportunite.PROJET
        self.opportunity.save(update_fields=["type_opportunite"])

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resume_is_required(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            self.apply_url,
            {"contact_email": "candidate@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv_id", response.data)

    def test_duplicate_application_returns_conflict(self):
        self.client.force_authenticate(self.candidate)
        Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            cv=self.resume,
        )

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_organization_account_is_forbidden(self):
        self.client.force_authenticate(self.organization)

        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        response = self.client.post(self.apply_url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_resume_owned_by_another_candidate_is_rejected(self):
        other_candidate = Utilisateur.objects.create_user(
            username="other-candidate",
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        other_resume = ProfileResume.objects.create(
            profile=other_candidate.profil,
            file=SimpleUploadedFile(
                "other.pdf",
                b"%PDF-1.4 other resume",
                content_type="application/pdf",
            ),
            is_active=True,
        )
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            self.apply_url,
            self._payload(cv_id=other_resume.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cv_id", response.data)

    def test_foreign_cover_letter_url_is_rejected(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            self.apply_url,
            self._payload(
                cover_letter_url="https://example.com/application_cover_letters/999/file.pdf",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cover_letter_url", response.data)

    def test_invalid_phone_is_rejected(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.post(
            self.apply_url,
            self._payload(contact_phone="-20"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("contact_phone", response.data)
