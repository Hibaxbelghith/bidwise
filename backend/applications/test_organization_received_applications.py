from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite
from users.models import OrganizationProfile, ProfileResume, Utilisateur

from .models import Candidature, StatutSuiviCandidature


@override_settings(PROFILE_RESUME_USE_CLOUDINARY=False)
class OrganizationReceivedApplicationListEndpointTests(APITestCase):
    def setUp(self):
        self.organization = Utilisateur.objects.create_user(
            username="received-applications-organization",
            email="organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        self.other_organization = Utilisateur.objects.create_user(
            username="received-applications-other-organization",
            email="other-organization@example.com",
            password="pass1234",
            account_type=Utilisateur.AccountType.ORGANIZATION,
        )
        OrganizationProfile.objects.create(
            user=self.organization,
            organization_name="Acme Tunisia",
            first_name="Hiba",
            last_name="Belghith",
            phone="+21612345678",
            organization_type=OrganizationProfile.OrganizationType.COMPANY,
        )
        OrganizationProfile.objects.create(
            user=self.other_organization,
            organization_name="Other Company",
            first_name="Sami",
            last_name="Ben Ali",
            phone="+21687654321",
            organization_type=OrganizationProfile.OrganizationType.COMPANY,
        )
        self.candidate = self._create_candidate(
            username="received-applications-candidate",
            email="candidate@example.com",
            first_name="Hiba",
            last_name="Belghith",
        )
        self.other_candidate = self._create_candidate(
            username="received-applications-other-candidate",
            email="other-candidate@example.com",
            first_name="Sami",
            last_name="Ben Ali",
        )
        source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )
        self.opportunity = self._create_opportunity(
            title="Backend Developer",
            organization=self.organization,
            source=source,
        )
        self.other_opportunity = self._create_opportunity(
            title="Frontend Developer",
            organization=self.other_organization,
            source=source,
        )

    @staticmethod
    def _create_candidate(*, username, email, first_name, last_name):
        candidate = Utilisateur.objects.create_user(
            username=username,
            email=email,
            password="pass1234",
            account_type=Utilisateur.AccountType.CANDIDATE,
            first_name=first_name,
            last_name=last_name,
        )
        candidate.profil.prenom = first_name
        candidate.profil.nom = last_name
        candidate.profil.save(update_fields=["prenom", "nom"])
        return candidate

    @staticmethod
    def _create_opportunity(*, title, organization, source):
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

    @staticmethod
    def _url(opportunity):
        return f"/api/organization/opportunities/{opportunity.pk}/applications/"

    @staticmethod
    def _create_resume(candidate, filename):
        return ProfileResume.objects.create(
            profile=candidate.profil,
            file=SimpleUploadedFile(
                filename,
                b"%PDF-1.4 candidate resume",
                content_type="application/pdf",
            ),
            is_active=True,
        )

    def test_empty_application_list_returns_empty_array(self):
        self.client.force_authenticate(self.organization)

        response = self.client.get(self._url(self.opportunity))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_application_list_returns_expected_fields(self):
        resume = self._create_resume(self.candidate, "hiba-resume.pdf")
        application = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=timezone.now(),
            cv=resume,
            contact_phone="+21612345678",
            cover_letter_url="https://example.com/cover-letter.pdf",
        )
        self.client.force_authenticate(self.organization)

        response = self.client.get(self._url(self.opportunity))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        item = response.data[0]
        self.assertEqual(
            set(item),
            {
                "id",
                "candidate_name",
                "candidate_email",
                "contact_phone",
                "statut",
                "submitted_at",
                "cv_url",
                "cover_letter_url",
            },
        )
        self.assertEqual(item["id"], application.pk)
        self.assertEqual(item["candidate_name"], "Hiba Belghith")
        self.assertEqual(item["candidate_email"], "candidate@example.com")
        self.assertEqual(item["contact_phone"], "+21612345678")
        self.assertEqual(item["statut"], StatutSuiviCandidature.SUBMITTED)
        self.assertIn(
            f"/profile_resumes/{self.candidate.profil.pk}/",
            item["cv_url"],
        )
        self.assertTrue(item["cv_url"].endswith(".pdf"))
        self.assertEqual(
            item["cover_letter_url"],
            "https://example.com/cover-letter.pdf",
        )

    def test_other_organization_opportunity_returns_not_found(self):
        self.client.force_authenticate(self.organization)

        response = self.client.get(self._url(self.other_opportunity))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_candidate_account_is_forbidden(self):
        self.client.force_authenticate(self.candidate)

        response = self.client.get(self._url(self.opportunity))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_user_is_unauthorized(self):
        response = self.client.get(self._url(self.opportunity))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_multiple_candidates_are_returned_in_submission_order(self):
        now = timezone.now()
        older = Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=now - timedelta(hours=1),
        )
        newer = Candidature.objects.create(
            candidat=self.other_candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            submitted_at=now,
        )
        self.client.force_authenticate(self.organization)

        response = self.client.get(self._url(self.opportunity))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data],
            [newer.pk, older.pk],
        )

    def test_organization_dashboard_returns_total_and_new_application_counts(self):
        Candidature.objects.create(
            candidat=self.candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.SUBMITTED,
            submitted_at=timezone.now(),
        )
        Candidature.objects.create(
            candidat=self.other_candidate,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.VIEWED_BY_ORGANIZATION,
            submitted_at=timezone.now() - timedelta(minutes=5),
        )
        self.client.force_authenticate(self.organization)

        response = self.client.get("/api/organization/opportunities/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        opportunity = next(
            item for item in response.data if item["id"] == self.opportunity.pk
        )
        self.assertEqual(opportunity["applications_count"], 2)
        self.assertEqual(opportunity["new_applications_count"], 1)
