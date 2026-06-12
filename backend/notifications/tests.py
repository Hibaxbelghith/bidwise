from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from notifications.models import (
    Notification,
    RecommendationNotificationDispatch,
    TypeNotification,
)
from notifications.tasks import send_recommendation_digest_task
from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from users.models import Profil, Utilisateur


@override_settings(
    RECOMMENDATION_DIGEST_MIN_PROFILE_SCORE=60,
    RECOMMENDATION_DIGEST_CANDIDATE_LIMIT=10,
    RECOMMENDATION_DIGEST_MAX_ITEMS=5,
    RECOMMENDATION_DIGEST_MIN_NEW_ITEMS=3,
    RECOMMENDATION_DIGEST_RECENT_DAYS=7,
)
class RecommendationDigestTaskTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="candidate_digest",
            email="candidate@example.com",
            password="secret123",
            account_type=Utilisateur.AccountType.CANDIDATE,
        )
        self.profile = self.user.profil
        self.profile.prenom = "Hiba"
        self.profile.nom = "Belghith"
        self.profile.save(update_fields=["prenom", "nom"])
        self.source = SourceOpportunite.objects.create(
            nom="BidWise Organizations",
            url="https://bidwise.local/opportunities",
            type_source="SITE_EMPLOI",
        )
        today = timezone.localdate()
        self.opportunity_1 = self._create_opportunity("Python Developer", today)
        self.opportunity_2 = self._create_opportunity("Backend Engineer", today - timedelta(days=1))
        self.opportunity_3 = self._create_opportunity("Data Analyst", today - timedelta(days=2))
        self.old_opportunity = self._create_opportunity("Old Opportunity", today - timedelta(days=30))

    def _create_opportunity(self, title, published_date):
        return Opportunite.objects.create(
            titre=title,
            description=f"{title} description",
            organisation_nom="Acme",
            ville="Tunis",
            type_opportunite=TypeOpportunite.EMPLOI,
            statut=StatutOpportunite.ACTIVE,
            date_publication=published_date,
            source=self.source,
        )

    def _recommendation_payload(self, opportunity, **overrides):
        payload = {
            "id": opportunity.id,
            "title": opportunity.titre,
            "company": opportunity.organisation_nom,
            "location": opportunity.ville,
            "statut": opportunity.statut,
            "recommendation_mode": "SEMANTIC",
            "date_publication": opportunity.date_publication.isoformat(),
        }
        payload.update(overrides)
        return payload

    @patch("notifications.tasks.send_mail")
    @patch("notifications.tasks.calculate_profile_completion")
    @patch("notifications.tasks.build_recommendations_for_user")
    def test_sends_digest_when_three_new_recent_items_exist(
        self,
        mock_build_recommendations,
        mock_profile_completion,
        mock_send_mail,
    ):
        mock_profile_completion.return_value = {"score": 85}
        mock_build_recommendations.return_value = [
            self._recommendation_payload(self.opportunity_1),
            self._recommendation_payload(self.opportunity_2),
            self._recommendation_payload(self.opportunity_3),
        ]

        result = send_recommendation_digest_task()

        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get()
        self.assertEqual(notification.utilisateur, self.user)
        self.assertEqual(notification.type_notification, TypeNotification.RECOMMANDATION)
        self.assertEqual(
            RecommendationNotificationDispatch.objects.filter(utilisateur=self.user).count(),
            3,
        )
        mock_send_mail.assert_called_once()

    @patch("notifications.tasks.send_mail")
    @patch("notifications.tasks.calculate_profile_completion")
    @patch("notifications.tasks.build_recommendations_for_user")
    def test_does_not_resend_same_opportunities(
        self,
        mock_build_recommendations,
        mock_profile_completion,
        mock_send_mail,
    ):
        mock_profile_completion.return_value = {"score": 85}
        dispatch = RecommendationNotificationDispatch.objects.create(
            utilisateur=self.user,
            opportunite=self.opportunity_1,
        )
        RecommendationNotificationDispatch.objects.filter(pk=dispatch.pk).update(
            sent_at=timezone.now() - timedelta(days=2)
        )
        mock_build_recommendations.return_value = [
            self._recommendation_payload(self.opportunity_1),
            self._recommendation_payload(self.opportunity_2),
            self._recommendation_payload(self.opportunity_3),
        ]

        result = send_recommendation_digest_task()

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped_not_enough_items"], 1)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(RecommendationNotificationDispatch.objects.count(), 1)
        mock_send_mail.assert_not_called()

    @patch("notifications.tasks.send_mail")
    @patch("notifications.tasks.calculate_profile_completion")
    @patch("notifications.tasks.build_recommendations_for_user")
    def test_does_not_send_more_than_once_per_day(
        self,
        mock_build_recommendations,
        mock_profile_completion,
        mock_send_mail,
    ):
        mock_profile_completion.return_value = {"score": 85}
        RecommendationNotificationDispatch.objects.create(
            utilisateur=self.user,
            opportunite=self.opportunity_1,
        )
        mock_build_recommendations.return_value = [
            self._recommendation_payload(self.opportunity_1),
            self._recommendation_payload(self.opportunity_2),
            self._recommendation_payload(self.opportunity_3),
        ]

        result = send_recommendation_digest_task()

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped_rate_limited"], 1)
        mock_send_mail.assert_not_called()

    @patch("notifications.tasks.send_mail")
    @patch("notifications.tasks.calculate_profile_completion")
    @patch("notifications.tasks.build_recommendations_for_user")
    def test_filters_out_old_inactive_and_fallback_items(
        self,
        mock_build_recommendations,
        mock_profile_completion,
        mock_send_mail,
    ):
        mock_profile_completion.return_value = {"score": 85}
        mock_build_recommendations.return_value = [
            self._recommendation_payload(self.opportunity_1, recommendation_mode="FALLBACK"),
            self._recommendation_payload(self.opportunity_2, statut=StatutOpportunite.SUSPENDUE),
            self._recommendation_payload(self.old_opportunity),
            self._recommendation_payload(self.opportunity_3),
        ]

        result = send_recommendation_digest_task()

        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped_not_enough_items"], 1)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(RecommendationNotificationDispatch.objects.count(), 0)
        mock_send_mail.assert_not_called()
