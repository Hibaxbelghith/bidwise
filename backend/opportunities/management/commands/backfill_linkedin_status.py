import logging
from urllib.parse import urlparse, urlunparse

from django.core.management.base import BaseCommand
from django.utils import timezone

from opportunities.models import Opportunite, StatutOpportunite
from opportunities.scraping.sources.linkedin import (
    _build_session,
    _rate_limit_delay,
    parse_linkedin_job_detail_html,
)


logger = logging.getLogger(__name__)


def _linkedin_url_variants(url):
    cleaned_url = str(url or "").strip()
    if not cleaned_url:
        return []

    try:
        parsed = urlparse(cleaned_url)
    except ValueError:
        return [cleaned_url]

    hostname = (parsed.netloc or "").lower()
    if hostname.endswith("linkedin.com") and hostname != "www.linkedin.com":
        www_url = urlunparse(parsed._replace(netloc="www.linkedin.com"))
        return [www_url, cleaned_url] if www_url != cleaned_url else [cleaned_url]

    return [cleaned_url]


class Command(BaseCommand):
    help = (
        "Refresh LinkedIn opportunity availability from detail pages and mark closed "
        "or unavailable postings as expired."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="LinkedIn",
            help="Source name fragment to target (default: LinkedIn).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of opportunities to inspect.",
        )
        parser.add_argument(
            "--ids",
            nargs="+",
            type=int,
            help="Optional explicit opportunity IDs to refresh.",
        )
        parser.add_argument(
            "--all-statuses",
            action="store_true",
            help="Process all statuses. By default only ACTIVE opportunities are inspected.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply updates. Without this flag, runs in dry-run mode.",
        )
        parser.add_argument(
            "--reactivate-open",
            action="store_true",
            help=(
                "Reactivate expired LinkedIn opportunities when the detail page is reachable, "
                "does not contain a closed-applications signal, and has no past deadline."
            ),
        )

    def handle(self, *args, **options):
        source_name = str(options.get("source") or "LinkedIn").strip()
        limit = max(1, int(options.get("limit") or 200))
        explicit_ids = options.get("ids") or []
        all_statuses = bool(options.get("all_statuses"))
        apply_changes = bool(options.get("apply"))
        reactivate_open = bool(options.get("reactivate_open"))

        queryset = (
            Opportunite.objects.select_related("source")
            .filter(source__nom__icontains=source_name)
            .exclude(source_item_url__isnull=True)
            .exclude(source_item_url="")
        )
        if explicit_ids:
            queryset = queryset.filter(id__in=explicit_ids)
        elif not all_statuses:
            queryset = queryset.filter(statut=StatutOpportunite.ACTIVE)

        target_ids = list(queryset.order_by("id").values_list("id", flat=True)[:limit])
        if not target_ids:
            self.stdout.write(self.style.WARNING("No LinkedIn opportunities matched the refresh scope."))
            return

        session = _build_session()
        stats = {
            "inspected": 0,
            "updated": 0,
            "no_change": 0,
            "fetch_error": 0,
            "closed_applications_expired": 0,
            "source_unavailable_expired": 0,
            "reactivated_open": 0,
            "save_error": 0,
        }

        self.stdout.write(
            f"Starting LinkedIn status refresh count={len(target_ids)} "
            f"mode={'apply' if apply_changes else 'dry-run'}"
        )

        for opportunity in Opportunite.objects.filter(id__in=target_ids).order_by("id"):
            stats["inspected"] += 1
            source_item_url = str(opportunity.source_item_url or "").strip()

            reason = ""
            saw_success = False
            saw_open = False
            unavailable_status_code = None
            fetch_failed = False

            for detail_url in _linkedin_url_variants(source_item_url):
                try:
                    _rate_limit_delay()
                    response = session.get(detail_url, timeout=15)
                    status_code = response.status_code
                except Exception as exc:  # noqa: BLE001
                    fetch_failed = True
                    logger.warning(
                        "linkedin_status_refresh_failed opportunity_id=%s url=%s error=%s",
                        opportunity.pk,
                        detail_url,
                        exc,
                    )
                    continue

                if status_code in {404, 410}:
                    unavailable_status_code = status_code
                    continue
                if status_code >= 400:
                    fetch_failed = True
                    logger.warning(
                        "LinkedIn status refresh skipped opportunity_id=%s url=%s status=%s",
                        opportunity.pk,
                        detail_url,
                        status_code,
                    )
                    continue

                saw_success = True
                detail_data = parse_linkedin_job_detail_html(response.text, job_url=detail_url)
                if detail_data.get("status") == StatutOpportunite.EXPIREE:
                    reason = "linkedin_closed_applications"
                    break
                saw_open = True

            if not reason and not saw_success and unavailable_status_code:
                reason = f"source_http_{unavailable_status_code}"
            elif not reason and not saw_success and fetch_failed:
                stats["fetch_error"] += 1
                continue

            if (
                reactivate_open
                and saw_open
                and opportunity.statut == StatutOpportunite.EXPIREE
                and (not opportunity.date_limite or opportunity.date_limite >= timezone.localdate())
            ):
                extra_data = dict(opportunity.extra_data or {})
                expiration = dict(extra_data.get("expiration") or {})
                if expiration:
                    expiration["reactivated_on"] = timezone.localdate().isoformat()
                    expiration["reactivation_reason"] = "linkedin_detail_page_open"
                    extra_data["expiration"] = expiration
                else:
                    extra_data["expiration"] = {
                        "reactivated_on": timezone.localdate().isoformat(),
                        "reactivation_reason": "linkedin_detail_page_open",
                        "source": "LinkedIn",
                    }
                opportunity.extra_data = extra_data
                opportunity.statut = StatutOpportunite.ACTIVE
                if apply_changes:
                    opportunity.date_modification = timezone.now()
                    opportunity.save(update_fields=["statut", "extra_data", "date_modification"])
                stats["updated"] += 1
                stats["reactivated_open"] += 1
                continue

            if not reason:
                stats["no_change"] += 1
                continue

            update_fields = []
            extra_data = dict(opportunity.extra_data or {})
            expiration = dict(extra_data.get("expiration") or {})
            next_expiration = {
                **expiration,
                "reason": reason,
                "expired_on": timezone.localdate().isoformat(),
                "automatic": True,
                "source": "LinkedIn",
            }
            if extra_data.get("expiration") != next_expiration:
                extra_data["expiration"] = next_expiration
                opportunity.extra_data = extra_data
                update_fields.append("extra_data")

            if opportunity.statut != StatutOpportunite.EXPIREE:
                opportunity.statut = StatutOpportunite.EXPIREE
                update_fields.append("statut")

            if not update_fields:
                stats["no_change"] += 1
                continue

            if apply_changes:
                opportunity.date_modification = timezone.now()
                update_fields.append("date_modification")
                opportunity.save(update_fields=update_fields)

            stats["updated"] += 1
            if reason == "linkedin_closed_applications":
                stats["closed_applications_expired"] += 1
            else:
                stats["source_unavailable_expired"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                "LinkedIn status refresh finished "
                f"(inspected={stats['inspected']}, updated={stats['updated']}, "
                f"no_change={stats['no_change']}, fetch_error={stats['fetch_error']}, "
                f"closed_applications_expired={stats['closed_applications_expired']}, "
                f"source_unavailable_expired={stats['source_unavailable_expired']}, "
                f"reactivated_open={stats['reactivated_open']}, "
                f"save_error={stats['save_error']})"
            )
        )
