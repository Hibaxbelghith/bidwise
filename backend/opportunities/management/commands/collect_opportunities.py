from django.core.management.base import BaseCommand

from opportunities.pipeline import (
    get_configured_sources,
    get_default_source,
    normalize_source,
    resolve_source_collection,
    run_opportunity_pipeline,
)


def collect_opportunities_pipeline(**options):
    return run_opportunity_pipeline(**options)


class Command(BaseCommand):
    help = "Collect opportunities from configured scrapers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=None,
            help=f"Scraper source key. Defaults to all configured sources, starting with {get_default_source()}.",
        )
        parser.add_argument(
            "--respect-schedule",
            action="store_true",
            help="Skip sources that are not due according to source schedule settings.",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=None,
            help="Optional max pages to scrape for sources that support pagination.",
        )
        parser.add_argument(
            "--keyword",
            default=None,
            help="Optional search keyword for sources that support keyword-based search.",
        )
        parser.add_argument(
            "--location",
            default=None,
            help="Optional search location for sources that support location-based search.",
        )
        parser.add_argument(
            "--max-records",
            type=int,
            default=None,
            help="Optional max records to collect for sources that support record caps.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=None,
            help="Optional request timeout in seconds for sources that support it.",
        )
        parser.add_argument(
            "--min-delay",
            type=float,
            default=None,
            help="Optional minimum delay between HTTP requests in seconds.",
        )
        parser.add_argument(
            "--max-delay",
            type=float,
            default=None,
            help="Optional maximum delay between HTTP requests in seconds.",
        )
        parser.add_argument(
            "--stage-only",
            action="store_true",
            help="Collect only internship-oriented listings for scrapers that support this mode.",
        )
        parser.add_argument(
            "--fetch-details",
            action="store_true",
            default=None,
            help="Fetch detail pages for sources that support detail enrichment.",
        )

    def handle(self, *args, **options):
        source = options.pop("source", None)
        respect_schedule = options.pop("respect_schedule", False)
        selected_sources = [normalize_source(source)] if source else get_configured_sources()

        for source_key in selected_sources:
            collection = resolve_source_collection(source_key, **options)
            scraper_kwargs = collection["scraper_kwargs"]
            self.stdout.write(
                f"Prepared collection source '{source_key}' with options: {scraper_kwargs or 'default'}"
            )

        results = run_opportunity_pipeline(
            selected_sources,
            respect_schedule=respect_schedule,
            **options,
        )

        if not results:
            self.stdout.write(self.style.WARNING("No source is due for collection."))
            return

        self.stdout.write(self.style.SUCCESS("Opportunity collection completed."))
        for collection in results:
            source_key = collection["source"]
            stats = collection["stats"]
            self.stdout.write(f"[{source_key}] Created: {stats['created']}")
            self.stdout.write(f"[{source_key}] Updated: {stats['updated']}")
            self.stdout.write(f"[{source_key}] Skipped: {stats['skipped']}")
            self.stdout.write(f"[{source_key}] Failed pages: {stats.get('failed_pages', 0)}")

            if stats["errors"]:
                self.stdout.write(self.style.WARNING(f"[{source_key}] Normalization warnings:"))
                for error in stats["errors"]:
                    self.stdout.write(f"- {error}")
