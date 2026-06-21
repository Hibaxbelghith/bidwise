from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from opportunities.models import (
    Opportunite,
    SourceOpportunite,
    StatutOpportunite,
    TypeOpportunite,
)
from opportunities.organization_expiration import expire_due_opportunities, expire_due_organization_opportunities


class OrganizationOpportunityExpirationTests(TestCase):
    def setUp(self):
        self.today = date(2026, 6, 8)
        self.organization = get_user_model().objects.create_user(
            username="expiration-org",
            email="expiration-org@example.com",
            account_type="organization",
        )
        self.source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/organizations",
            type_source="AUTRE",
        )

    def create_opportunity(self, **overrides):
        values = {
            "titre": "Organization opportunity",
            "description": "A complete professional opportunity description.",
            "organisation_nom": "Expiration Org",
            "type_opportunite": TypeOpportunite.EMPLOI,
            "statut": StatutOpportunite.ACTIVE,
            "date_publication": self.today - timedelta(days=10),
            "date_limite": None,
            "organisation": self.organization,
            "source": self.source,
            "extra_data": {"published_by": "organization"},
        }
        values.update(overrides)
        return Opportunite.objects.create(**values)

    def test_expiration_is_strictly_after_deadline(self):
        past = self.create_opportunity(date_limite=self.today - timedelta(days=1))
        today = self.create_opportunity(date_limite=self.today)
        future = self.create_opportunity(date_limite=self.today + timedelta(days=1))

        result = expire_due_organization_opportunities(today=self.today)

        past.refresh_from_db()
        today.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(past.statut, StatutOpportunite.EXPIREE)
        self.assertEqual(today.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(future.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(result["expired_ids"], [past.id])

    def test_seasonal_end_date_expires_seasonal_opportunity(self):
        seasonal = self.create_opportunity(
            type_opportunite=TypeOpportunite.SAISONNIER,
            extra_data={
                "published_by": "organization",
                "seasonal_details": {
                    "season": "SUMMER",
                    "start_date": (self.today - timedelta(days=30)).isoformat(),
                    "end_date": (self.today - timedelta(days=1)).isoformat(),
                },
            },
        )

        expire_due_organization_opportunities(today=self.today)

        seasonal.refresh_from_db()
        self.assertEqual(seasonal.statut, StatutOpportunite.EXPIREE)
        self.assertEqual(
            seasonal.extra_data["expiration"]["reason"],
            "seasonal_end_date",
        )

    def test_non_active_and_scraped_opportunities_are_preserved(self):
        suspended = self.create_opportunity(
            statut=StatutOpportunite.SUSPENDUE,
            date_limite=self.today - timedelta(days=1),
        )
        scraped = self.create_opportunity(
            organisation=None,
            date_limite=self.today - timedelta(days=1),
        )

        result = expire_due_organization_opportunities(today=self.today)

        suspended.refresh_from_db()
        scraped.refresh_from_db()
        self.assertEqual(suspended.statut, StatutOpportunite.SUSPENDUE)
        self.assertEqual(scraped.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(result["expired"], 0)

    def test_global_expiration_can_expire_scraped_projects(self):
        marches = SourceOpportunite.objects.create(
            nom="MarchesPublics",
            url="https://www.marchespublics.gov.tn",
            type_source="PORTAIL_PROJET",
        )
        scraped_project = self.create_opportunity(
            organisation=None,
            source=marches,
            type_opportunite=TypeOpportunite.PROJET,
            date_limite=self.today - timedelta(days=1),
        )
        future_project = self.create_opportunity(
            organisation=None,
            source=marches,
            type_opportunite=TypeOpportunite.PROJET,
            date_limite=self.today + timedelta(days=1),
        )

        result = expire_due_opportunities(
            today=self.today,
            type_opportunite=TypeOpportunite.PROJET,
            apply_changes=True,
        )

        scraped_project.refresh_from_db()
        future_project.refresh_from_db()
        self.assertEqual(scraped_project.statut, StatutOpportunite.EXPIREE)
        self.assertEqual(future_project.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(result["expired_ids"], [scraped_project.id])

    def test_global_expiration_can_expire_scraped_jobs_and_internships(self):
        linkedin = SourceOpportunite.objects.create(
            nom="LinkedIn",
            url="https://www.linkedin.com/jobs",
            type_source="PORTAIL_EMPLOI",
        )
        scraped_job = self.create_opportunity(
            organisation=None,
            source=linkedin,
            type_opportunite=TypeOpportunite.EMPLOI,
            date_limite=self.today - timedelta(days=1),
        )
        scraped_internship = self.create_opportunity(
            organisation=None,
            source=linkedin,
            type_opportunite=TypeOpportunite.STAGE,
            date_limite=self.today - timedelta(days=1),
        )
        future_job = self.create_opportunity(
            organisation=None,
            source=linkedin,
            type_opportunite=TypeOpportunite.EMPLOI,
            date_limite=self.today + timedelta(days=1),
        )

        result = expire_due_opportunities(today=self.today, apply_changes=True)

        scraped_job.refresh_from_db()
        scraped_internship.refresh_from_db()
        future_job.refresh_from_db()
        self.assertEqual(scraped_job.statut, StatutOpportunite.EXPIREE)
        self.assertEqual(scraped_internship.statut, StatutOpportunite.EXPIREE)
        self.assertEqual(future_job.statut, StatutOpportunite.ACTIVE)
        self.assertEqual(result["expired_ids"], [scraped_job.id, scraped_internship.id])
