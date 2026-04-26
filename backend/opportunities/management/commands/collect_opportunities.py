import inspect

from django.core.management.base import BaseCommand, CommandError

from opportunities.scraping.sources import (
    EmploiTunisieScraper,
    KeejobScraper,
    LinkedInScraper,
    MarchesPublicsScraper,
)
from opportunities.scraping.pipeline import run_collection

SCRAPER_REGISTRY = {
    "emploitunisie": EmploiTunisieScraper,
    "keejob": KeejobScraper,
    "linkedin": LinkedInScraper,
    "marchespublics": MarchesPublicsScraper,
}


class Command(BaseCommand):
    help = "Collect opportunities from configured scrapers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="keejob",
            help="Scraper source key (default: keejob).",
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
        source_key = options["source"].lower().strip()
        scraper_cls = SCRAPER_REGISTRY.get(source_key)

        if not scraper_cls:
            valid = ", ".join(sorted(SCRAPER_REGISTRY.keys()))
            raise CommandError(f"Unknown source '{source_key}'. Available: {valid}")

        requested_kwargs = {
            "max_pages": options.get("max_pages"),
            "keyword": options.get("keyword"),
            "location": options.get("location"),
            "max_records": options.get("max_records"),
            "timeout": options.get("timeout"),
            "min_delay": options.get("min_delay"),
            "max_delay": options.get("max_delay"),
            "stage_only": options.get("stage_only"),
            "fetch_details": options.get("fetch_details"),
        }
        init_signature = inspect.signature(scraper_cls.__init__)
        scraper_kwargs = {
            key: value
            for key, value in requested_kwargs.items()
            if value is not None and key in init_signature.parameters
        }

        self.stdout.write(
            f"Starting collection from '{source_key}' with options: {scraper_kwargs or 'default'}"
        )
        scraper = scraper_cls(**scraper_kwargs)
        stats = run_collection(scraper=scraper)

        self.stdout.write(self.style.SUCCESS("Opportunity collection completed."))
        self.stdout.write(f"Created: {stats['created']}")
        self.stdout.write(f"Updated: {stats['updated']}")
        self.stdout.write(f"Skipped: {stats['skipped']}")

        if stats["errors"]:
            self.stdout.write(self.style.WARNING("Normalization warnings:"))
            for error in stats["errors"]:
                self.stdout.write(f"- {error}")
