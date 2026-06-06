from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from applications.models import Candidature, StatutSuiviCandidature
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.services.scheduler_monitoring import (
    cache_scheduler_decision_snapshot,
    scheduler_decision_cache_key,
    serialize_scheduler_decision,
)
from opportunities.utils.images import DEFAULT_COMPANY_LOGO_URL


User = get_user_model()


class AdminApiTests(APITestCase):
    def setUp(self):
        cache.clear()
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

    def tearDown(self):
        cache.clear()

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
        self.assertEqual(result["type"], TypeOpportunite.EMPLOI)
        self.assertEqual(result["status"], StatutOpportunite.ACTIVE)
        self.assertEqual(result["url"], self.opportunity.source_item_url)
        self.assertEqual(result["company_name"], "BidWise")
        self.assertEqual(result["published_by"], "scraper")
        self.assertIsNone(result["organization_email"])
        self.assertIsNone(result["moderation_summary"])

        delete_response = self.client.delete(f"/api/admin/opportunities/{self.opportunity.id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Opportunite.objects.filter(id=self.opportunity.id).exists())

    def test_admin_opportunities_include_organization_moderation_summary(self):
        self.client.force_authenticate(self.admin)
        organization = User.objects.create_user(
            username="org@example.com",
            email="org@example.com",
            password="password",
            account_type=User.AccountType.ORGANIZATION,
        )
        pending = Opportunite.objects.create(
            titre="PFE Platform Engineer",
            description="Ambiguous organization post",
            organisation_nom="Acme Tunisia",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.PENDING_REVIEW,
            date_publication=date.today(),
            source=self.keejob,
            organisation=organization,
            extra_data={
                "published_by": "organization",
                "moderation": {
                    "llm": {
                        "skipped": False,
                        "category": "scam",
                        "decision": "rejected",
                        "confidence": 0.9,
                        "reason": "The candidate is asked to pay money before starting.",
                        "provider": "gemini",
                        "model": "gemini-test",
                    },
                    "final_decision": "rejected",
                    "final_status": StatutOpportunite.PENDING_REVIEW,
                },
            },
        )

        response = self.client.get("/api/admin/opportunities/", {"search": "PFE"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        result = response.data["results"][0]
        self.assertEqual(result["id"], pending.id)
        self.assertEqual(result["type"], TypeOpportunite.EMPLOI)
        self.assertEqual(result["status"], StatutOpportunite.PENDING_REVIEW)
        self.assertEqual(result["published_by"], "organization")
        self.assertEqual(result["organization_email"], "org@example.com")
        self.assertEqual(result["moderation_summary"]["final_decision"], "rejected")
        self.assertEqual(result["moderation_summary"]["category"], "scam")
        self.assertEqual(result["moderation_summary"]["decision"], "rejected")
        self.assertEqual(result["moderation_summary"]["confidence"], 0.9)
        self.assertEqual(result["moderation_summary"]["provider"], "gemini")

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

    def test_admin_dashboard_reports_platform_global_statistics(self):
        Candidature.objects.create(
            candidat=self.user,
            opportunite=self.opportunity,
            statut=StatutSuiviCandidature.INTERESSEE,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/admin/dashboard/", {"view": "platform"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        platform = response.data["platform"]
        self.assertNotIn("monitoring", response.data)
        self.assertNotIn("celery", response.data)
        self.assertEqual(platform["users"]["total"], 2)
        self.assertEqual(platform["users"]["active"], 2)
        self.assertEqual(platform["users"]["admins"], 1)
        self.assertEqual(platform["users"]["candidates"], 1)
        self.assertEqual(platform["applications"]["total"], 1)
        self.assertEqual(platform["applications"]["by_status"]["INTERESSEE"], 1)
        self.assertEqual(platform["opportunities"]["total"], 2)
        self.assertEqual(platform["opportunities"]["active"], 2)
        self.assertEqual(platform["opportunities"]["by_type"][TypeOpportunite.EMPLOI], 2)
        self.assertAlmostEqual(platform["conversion"]["application_rate"], 50.0)
        self.assertEqual(len(platform["growth"]["users"]), 30)
        self.assertEqual(len(platform["growth"]["applications"]), 30)
        self.assertEqual(len(platform["growth"]["opportunities"]), 30)

    def test_scheduler_decision_serializer_returns_dashboard_contract(self):
        next_run_at = timezone.now()

        decision = serialize_scheduler_decision(
            {
                "source": "linkedin",
                "reason": "adaptive_high_created_volume",
                "interval_seconds": 1800,
                "next_run_at": next_run_at,
                "schedule_metrics": {
                    "recent_created_avg": 25.0,
                    "recent_updated_avg": 40.5,
                    "failure_rate": 0.02,
                    "consecutive_zero_runs": 0,
                    "freshness_lag": 600,
                    "created_per_run": 12.5,
                    "trend": [2, 8, 15],
                },
                "score_history": [0.2, 0.5],
            }
        )

        self.assertEqual(
            decision,
            {
                "source": "linkedin",
                "reason": "ADAPTIVE_HIGH_CREATED_VOLUME",
                "interval_seconds": 1800,
                "next_run_at": next_run_at.isoformat(),
                "score_history": [0.2, 0.5],
                "metrics": {
                    "created_avg": 25,
                    "updated_avg": 40.5,
                    "failure_rate": 0.02,
                    "zero_runs": 0,
                    "freshness_lag": 600,
                    "created_per_run": 12.5,
                    "trend": [2, 8, 15],
                },
            },
        )

    @override_settings(OPPORTUNITY_PIPELINE_SOURCES=["linkedin", "keejob"])
    def test_admin_scheduler_state_reads_cache_and_falls_back_per_source(self):
        cached_decision = {
            "source": "linkedin",
            "reason": "NORMAL",
            "interval_seconds": 3600,
            "next_run_at": "2026-05-04T12:00:00+01:00",
            "score_history": [0.3, 0.6],
            "metrics": {
                "created_avg": 3,
                "updated_avg": 5,
                "failure_rate": 0.0,
                "zero_runs": 0,
                "freshness_lag": 120,
                "created_per_run": 3,
                "trend": [1, 2, 3],
            },
        }
        cache.set(scheduler_decision_cache_key("linkedin"), cached_decision, timeout=3600)

        self.client.force_authenticate(self.admin)
        with patch("opportunities.pipeline.get_source_schedule_state") as schedule_state_mock:
            response = self.client.get("/api/admin/scheduler-state/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule_state_mock.assert_not_called()
        self.assertEqual(response.data[0], cached_decision)
        self.assertEqual(
            response.data[1],
            {
                "source": "keejob",
                "reason": "NO_DATA",
                "interval_seconds": None,
                "next_run_at": None,
                "score_history": [],
                "metrics": {},
            },
        )

    @override_settings(OPPORTUNITY_SCHEDULER_DECISION_CACHE_TIMEOUT_SECONDS=1200)
    def test_scheduler_decision_cache_uses_configured_ttl(self):
        with patch("opportunities.services.scheduler_monitoring.cache.set") as cache_set:
            cache_scheduler_decision_snapshot(
                {
                    "source": "linkedin",
                    "reason": "scheduled",
                    "interval_seconds": 1800,
                    "next_run_at": timezone.now(),
                    "schedule_metrics": {"adaptive_score": 0.4},
                }
            )

        self.assertEqual(cache_set.call_args.kwargs["timeout"], 1200)

    @override_settings(OPPORTUNITY_SCHEDULER_SCORE_HISTORY_LIMIT=3)
    def test_scheduler_decision_cache_snapshot_exposes_score_history(self):
        for score in (0.2, 0.4, 0.7, 0.9):
            cache_scheduler_decision_snapshot(
                {
                    "source": "linkedin",
                    "reason": "scheduled",
                    "interval_seconds": 1800,
                    "next_run_at": timezone.now(),
                    "schedule_metrics": {
                        "adaptive_score": score,
                        "adaptive_raw_score": score * 10,
                    },
                }
            )

        cached = cache.get(scheduler_decision_cache_key("linkedin"))

        self.assertEqual(cached["score_history"], [0.4, 0.7, 0.9])
        self.assertEqual(cached["metrics"]["score"], 0.9)
