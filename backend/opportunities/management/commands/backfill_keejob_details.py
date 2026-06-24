import hashlib
import logging
from datetime import date

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from opportunities.models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite
from opportunities.scraping.sources import KeejobScraper
from opportunities.scraping.scraper_utils import canonicalize_source_item_url


logger = logging.getLogger(__name__)


def _build_external_id(source_item_url):
    url = canonicalize_source_item_url(source_item_url)
    if not url:
        return ""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _fetch_detail_soup_with_status(scraper, url):
    try:
        scraper._rate_limit_delay()
        response = scraper.session.get(url, timeout=scraper.timeout)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Request failed for %s: %s", url, exc)
        return None, None

    if response.status_code == 403:
        scraper.blocked = True
        logger.warning("[keejob] blocked (403), stopping")
        return None, response.status_code
    if response.status_code != 200:
        logger.warning("Request failed for %s status=%s", url, response.status_code)
        return None, response.status_code

    return BeautifulSoup(response.text, "html.parser"), response.status_code


class Command(BaseCommand):
    help = (
        "Backfill stale Keejob canonical fields by re-scraping each source_item_url "
        "(description, company_logo, description_html, type, statut, date_publication, date_limite, external_id)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="Keejob",
            help="Source name to target (default: Keejob).",
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
            help="Optional explicit opportunity IDs to backfill.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all opportunities for the source (not only potentially stale rows).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply updates. Without this flag, runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        source_name = str(options.get("source") or "Keejob").strip()
        limit = max(1, int(options.get("limit") or 200))
        explicit_ids = options.get("ids") or []
        force_all = bool(options.get("all"))
        apply_changes = bool(options.get("apply"))

        source = SourceOpportunite.objects.filter(nom=source_name).first()
        if source is None:
            self.stdout.write(self.style.ERROR(f"Source not found: {source_name}"))
            return

        queryset = Opportunite.objects.filter(source=source)
        queryset = queryset.exclude(source_item_url__isnull=True).exclude(source_item_url="")

        if explicit_ids:
            queryset = queryset.filter(id__in=explicit_ids)
        elif not force_all:
            queryset = queryset.filter(
                Q(company_logo="")
                | Q(description_html="")
                | Q(external_id="")
                | Q(statut=StatutOpportunite.ACTIVE)
            )

        target_ids = list(queryset.order_by("id").values_list("id", flat=True)[:limit])
        if not target_ids:
            self.stdout.write(self.style.WARNING("No opportunities matched the backfill scope."))
            return

        scraper = KeejobScraper(max_pages=1)
        stats = {
            "inspected": 0,
            "updated": 0,
            "no_change": 0,
            "fetch_error": 0,
            "source_404_expired": 0,
            "save_error": 0,
        }

        self.stdout.write(
            f"Starting detail backfill for source={source_name} count={len(target_ids)} "
            f"mode={'apply' if apply_changes else 'dry-run'}"
        )

        for opportunity in Opportunite.objects.filter(id__in=target_ids).order_by("id"):
            stats["inspected"] += 1
            source_item_url = canonicalize_source_item_url(opportunity.source_item_url)

            try:
                detail_soup, status_code = _fetch_detail_soup_with_status(scraper, source_item_url)
                if detail_soup is None:
                    if status_code == 404:
                        update_fields = []
                        extra_data = dict(opportunity.extra_data or {})
                        expiration = dict(extra_data.get("expiration") or {})
                        next_expiration = {
                            **expiration,
                            "reason": "source_404",
                            "expired_on": timezone.localdate().isoformat(),
                            "automatic": True,
                            "source": source_name,
                        }
                        if extra_data.get("expiration") != next_expiration:
                            extra_data["expiration"] = next_expiration
                            opportunity.extra_data = extra_data
                            update_fields.append("extra_data")
                        if opportunity.statut != StatutOpportunite.EXPIREE:
                            opportunity.statut = StatutOpportunite.EXPIREE
                            update_fields.append("statut")

                        if update_fields:
                            if apply_changes:
                                opportunity.date_modification = timezone.now()
                                update_fields.append("date_modification")
                                opportunity.save(update_fields=update_fields)
                            stats["updated"] += 1
                            stats["source_404_expired"] += 1
                        else:
                            stats["no_change"] += 1
                        continue

                    stats["fetch_error"] += 1
                    continue

                detail_company = scraper._extract_detail_company(detail_soup) or ""
                detail_logo = scraper._extract_detail_company_logo(
                    detail_soup,
                    source_item_url,
                    detail_company or opportunity.organisation_nom,
                ) or ""
                detail_html = scraper._extract_detail_description_html(detail_soup) or ""
                detail_text = scraper._extract_detail_description(detail_soup, detail_html) or ""
                detail_status = scraper._extract_detail_status(detail_soup) or opportunity.statut
                detail_contract_type = scraper._extract_detail_contract_type(detail_soup)
                detail_type = scraper._map_contract_to_opportunity_type(
                    detail_contract_type,
                    opportunity.titre,
                    opportunity.description,
                )
                detail_publication = scraper._extract_detail_publication_date(detail_soup)

                structured_fields = scraper._extract_structured_detail_fields(detail_soup) or {}
                detail_deadline_raw = structured_fields.get("deadline")
                detail_deadline = (
                    scraper._parse_date_value(detail_deadline_raw) if detail_deadline_raw else None
                )

                external_id = _build_external_id(source_item_url)
                update_fields = []

                if detail_logo and detail_logo != (opportunity.company_logo or ""):
                    opportunity.company_logo = detail_logo
                    update_fields.append("company_logo")

                if detail_text and detail_text != (opportunity.description or ""):
                    opportunity.description = detail_text
                    update_fields.append("description")

                if detail_html and detail_html != (opportunity.description_html or ""):
                    opportunity.description_html = detail_html
                    update_fields.append("description_html")

                if detail_status in StatutOpportunite.values and detail_status != opportunity.statut:
                    opportunity.statut = detail_status
                    update_fields.append("statut")

                normalized_contract_type = detail_contract_type or ""
                if normalized_contract_type != (opportunity.contract_type or ""):
                    opportunity.contract_type = normalized_contract_type
                    update_fields.append("contract_type")

                if detail_type in TypeOpportunite.values and detail_type != opportunity.type_opportunite:
                    opportunity.type_opportunite = detail_type
                    update_fields.append("type_opportunite")

                if detail_publication:
                    parsed_publication = date.fromisoformat(detail_publication)
                    if parsed_publication != opportunity.date_publication:
                        opportunity.date_publication = parsed_publication
                        update_fields.append("date_publication")

                if detail_deadline != opportunity.date_limite:
                    opportunity.date_limite = detail_deadline
                    update_fields.append("date_limite")

                if external_id and external_id != (opportunity.external_id or ""):
                    opportunity.external_id = external_id
                    update_fields.append("external_id")

                if source_item_url and source_item_url != (opportunity.source_item_url or ""):
                    opportunity.source_item_url = source_item_url
                    update_fields.append("source_item_url")

                if not update_fields:
                    stats["no_change"] += 1
                    continue

                if apply_changes:
                    opportunity.date_modification = timezone.now()
                    update_fields.append("date_modification")
                    opportunity.save(update_fields=update_fields)
                stats["updated"] += 1

            except Exception as exc:  # noqa: BLE001
                stats["save_error"] += 1
                logger.exception(
                    "keejob_detail_backfill_failed opportunity_id=%s url=%s error=%s",
                    opportunity.pk,
                    source_item_url,
                    exc,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill finished "
                f"(inspected={stats['inspected']}, updated={stats['updated']}, "
                f"no_change={stats['no_change']}, fetch_error={stats['fetch_error']}, "
                f"source_404_expired={stats['source_404_expired']}, "
                f"save_error={stats['save_error']})"
            )
        )
