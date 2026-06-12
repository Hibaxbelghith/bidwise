import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ai.views import build_recommendations_for_user
from users.models import Profil, Utilisateur
from users.profile_completion import calculate_profile_completion
from .models import (
    Notification,
    RecommendationNotificationDispatch,
    TypeNotification,
)
from .recommendation_emails import build_recommendation_digest_email


logger = logging.getLogger(__name__)

DEFAULT_RECENT_DAYS = 7
DEFAULT_LIMIT = 5
DEFAULT_CANDIDATE_LIMIT = 20
DEFAULT_MIN_NEW = 3
DEFAULT_MIN_PROFILE_SCORE = 60


def _setting_int(name, default):
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def _publication_is_recent(value, *, cutoff_date):
    text = str(value or "").strip()
    if not text:
        return False
    parsed = parse_date(text)
    if parsed is not None:
        return parsed >= cutoff_date
    parsed_dt = parse_datetime(text)
    if parsed_dt is not None:
        if timezone.is_naive(parsed_dt):
            parsed_dt = timezone.make_aware(parsed_dt, timezone.get_current_timezone())
        return parsed_dt.date() >= cutoff_date
    return False


def _profile_display_name(profile, user):
    first_name = str(getattr(profile, "prenom", "") or "").strip()
    if first_name:
        return first_name
    first_name = str(getattr(user, "first_name", "") or "").strip()
    if first_name:
        return first_name
    return "there"


def _select_digest_opportunities(user, *, recent_days, max_items, candidate_limit):
    cutoff_date = timezone.localdate() - timedelta(days=recent_days)
    already_sent_ids = set(
        RecommendationNotificationDispatch.objects.filter(utilisateur=user)
        .values_list("opportunite_id", flat=True)
    )
    recommendations = build_recommendations_for_user(user, limit=candidate_limit)
    selected = []

    for item in recommendations if isinstance(recommendations, list) else []:
        if not isinstance(item, dict):
            continue
        opportunity_id = int(item.get("id") or 0)
        if not opportunity_id or opportunity_id in already_sent_ids:
            continue
        if str(item.get("statut") or "").strip().upper() != "ACTIVE":
            continue
        if str(item.get("recommendation_mode") or "").strip().upper() == "FALLBACK":
            continue
        if not _publication_is_recent(item.get("date_publication"), cutoff_date=cutoff_date):
            continue

        selected.append(item)
        if len(selected) >= max_items:
            break

    return selected


@shared_task(
    bind=True,
    name="notifications.send_recommendation_digest",
    max_retries=0,
)
def send_recommendation_digest_task(self):
    min_profile_score = _setting_int("RECOMMENDATION_DIGEST_MIN_PROFILE_SCORE", DEFAULT_MIN_PROFILE_SCORE)
    candidate_limit = _setting_int("RECOMMENDATION_DIGEST_CANDIDATE_LIMIT", DEFAULT_CANDIDATE_LIMIT)
    max_items = _setting_int("RECOMMENDATION_DIGEST_MAX_ITEMS", DEFAULT_LIMIT)
    min_new = _setting_int("RECOMMENDATION_DIGEST_MIN_NEW_ITEMS", DEFAULT_MIN_NEW)
    recent_days = _setting_int("RECOMMENDATION_DIGEST_RECENT_DAYS", DEFAULT_RECENT_DAYS)
    today = timezone.localdate()

    stats = {
        "inspected": 0,
        "sent": 0,
        "skipped_rate_limited": 0,
        "skipped_incomplete_profile": 0,
        "skipped_email_missing": 0,
        "skipped_not_enough_items": 0,
        "failed": 0,
    }

    candidates = (
        Utilisateur.objects.filter(
            account_type=Utilisateur.AccountType.CANDIDATE,
            is_active=True,
        )
        .select_related("profil")
        .order_by("id")
    )

    for user in candidates.iterator():
        stats["inspected"] += 1
        try:
            profile = user.profil
        except Profil.DoesNotExist:
            stats["skipped_incomplete_profile"] += 1
            continue

        completion = calculate_profile_completion(profile)
        if int(completion.get("score") or 0) < min_profile_score:
            stats["skipped_incomplete_profile"] += 1
            continue

        if not str(user.email or "").strip():
            stats["skipped_email_missing"] += 1
            continue

        sent_today = RecommendationNotificationDispatch.objects.filter(
            utilisateur=user,
            sent_at__date=today,
        ).exists()
        if sent_today:
            stats["skipped_rate_limited"] += 1
            continue

        opportunities = _select_digest_opportunities(
            user,
            recent_days=recent_days,
            max_items=max_items,
            candidate_limit=candidate_limit,
        )
        if len(opportunities) < min_new:
            stats["skipped_not_enough_items"] += 1
            continue

        email = build_recommendation_digest_email(
            first_name=_profile_display_name(profile, user),
            opportunities=opportunities,
        )
        notification_id = None

        try:
            with transaction.atomic():
                notification = Notification.objects.create(
                    utilisateur=user,
                    type_notification=TypeNotification.RECOMMANDATION,
                    message=(
                        f"{len(opportunities)} new opportunities matching your profile are available."
                    ),
                )
                dispatches = []
                for item in opportunities:
                    dispatches.append(
                        RecommendationNotificationDispatch(
                            utilisateur=user,
                            opportunite_id=int(item["id"]),
                            notification=notification,
                        )
                    )
                RecommendationNotificationDispatch.objects.bulk_create(dispatches)
                notification_id = notification.pk

            send_mail(
                subject=email.subject,
                message=email.plaintext,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[str(user.email).strip()],
                fail_silently=False,
                html_message=email.html,
            )
            stats["sent"] += 1
            logger.info(
                "Recommendation digest sent user_id=%s opportunity_count=%s",
                user.pk,
                len(opportunities),
            )
        except IntegrityError:
            # Another concurrent run or retry recorded the same opportunity.
            stats["skipped_rate_limited"] += 1
            logger.info(
                "Recommendation digest skipped user_id=%s reason=duplicate_dispatch",
                user.pk,
            )
        except Exception:
            if notification_id is not None:
                RecommendationNotificationDispatch.objects.filter(notification_id=notification_id).delete()
                Notification.objects.filter(pk=notification_id).delete()
            stats["failed"] += 1
            logger.exception(
                "Recommendation digest failed user_id=%s",
                user.pk,
            )

    return stats
