from django.core.management.base import BaseCommand

from opportunities.models import Opportunite
from opportunities.normalization.industries import normalize_industries


class Command(BaseCommand):
    help = "Backfill normalized_industries from opportunity company sector metadata."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=500)
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recompute rows that already have normalized_industries.",
        )

    def handle(self, *args, **options):
        batch_size = max(1, int(options["batch_size"]))
        force = bool(options["force"])
        queryset = Opportunite.objects.only("id", "extra_data", "normalized_industries")
        if not force:
            queryset = queryset.filter(normalized_industries=[])

        scanned = 0
        updated = 0
        pending = []
        for opportunity in queryset.iterator(chunk_size=batch_size):
            scanned += 1
            extra_data = opportunity.extra_data if isinstance(opportunity.extra_data, dict) else {}
            industries = normalize_industries(extra_data.get("company_sector"))
            if industries == (opportunity.normalized_industries or []):
                continue
            opportunity.normalized_industries = industries
            pending.append(opportunity)
            if len(pending) >= batch_size:
                Opportunite.objects.bulk_update(pending, ["normalized_industries"], batch_size=batch_size)
                updated += len(pending)
                pending.clear()

        if pending:
            Opportunite.objects.bulk_update(pending, ["normalized_industries"], batch_size=batch_size)
            updated += len(pending)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilled normalized industries: scanned={scanned}, updated={updated}, force={force}"
            )
        )
