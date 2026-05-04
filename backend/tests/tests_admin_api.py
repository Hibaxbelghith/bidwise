from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.utils.images import DEFAULT_COMPANY_LOGO_URL


User = get_user_model()


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="password",
            is_admin=True,
        )
        self.user = User.objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="password",
        )
        self.linkedin = SourceOpportunite.objects.create(
            nom="linkedin",
            url="https://linkedin.com/jobs",
            type_source="SITE_EMPLOI",
        )
        self.keejob = SourceOpportunite.objects.create(
            nom="keejob",
            url="https://keejob.com",
            type_source="SITE_EMPLOI",
        )
        self.opportunity = Opportunite.objects.create(
            titre="Backend Django Developer",
            description="Build APIs",
            organisation_nom="BidWise",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source_item_url="https://linkedin.com/jobs/1",
            company_logo="https://linkedin.com/media/company/logo.png",
            source=self.linkedin,
        )
        Opportunite.objects.create(
            titre="Frontend React Developer",
            description="Build UI",
            organisation_nom="Acme",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            source=self.keejob,
        )

    def test_admin_opportunities_require_is_admin(self):
        response = self.client.get("/api/admin/opportunities/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.user)
        response = self.client.get("/api/admin/opportunities/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_filter_and_delete_opportunities(self):
        self.client.force_authenticate(self.admin)

        response = self.client.get(
            "/api/admin/opportunities/",
            {"search": "django", "source": self.linkedin.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["title"], self.opportunity.titre)
        self.assertEqual(
            result["source"],
            {
                "id": self.linkedin.id,
                "nom": "linkedin",
                "type_source": "SITE_EMPLOI",
            },
        )
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["url"], self.opportunity.source_item_url)
        self.assertEqual(result["company_name"], "BidWise")

        delete_response = self.client.delete(f"/api/admin/opportunities/{self.opportunity.id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Opportunite.objects.filter(id=self.opportunity.id).exists())

    def test_admin_can_toggle_user_admin_and_active_flags(self):
        self.client.force_authenticate(self.admin)

        admin_response = self.client.post(f"/api/admin/users/{self.user.id}/toggle-admin/")
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_admin)
        self.assertTrue(admin_response.data["is_admin"])

        active_response = self.client.post(f"/api/admin/users/{self.user.id}/toggle-active/")
        self.assertEqual(active_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(active_response.data["is_active"])

    def test_admin_cannot_disable_self(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/admin/users/{self.admin.id}/toggle-active/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_dashboard_reports_logo_coverage(self):
        Opportunite.objects.create(
            titre="Anonymous Company",
            description="No real company logo should count as placeholder coverage.",
            organisation_nom="Entreprise Anonyme",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=date.today(),
            company_logo=DEFAULT_COMPANY_LOGO_URL,
            source=self.keejob,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/admin/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        logo_metrics = response.data["monitoring"]["logos"]
        self.assertEqual(logo_metrics["total"], 3)
        self.assertEqual(logo_metrics["with_logo"], 1)
        self.assertEqual(logo_metrics["missing_or_placeholder"], 2)
        self.assertAlmostEqual(logo_metrics["coverage"], 100 / 3)
        self.assertAlmostEqual(response.data["kpis"]["logo_coverage"], 100 / 3)
