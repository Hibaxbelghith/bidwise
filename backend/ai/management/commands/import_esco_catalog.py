from pathlib import Path

from django.core.management.base import BaseCommand

from ai.esco_catalog_ingestion import import_esco_catalog
from ai.esco_skill_index import clear_esco_skill_index_cache


class Command(BaseCommand):
    help = "Import official raw ESCO CSV files into clean internal BidWise catalog tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            default=None,
            help="Directory containing raw ESCO CSV files.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Bulk create/update batch size.",
        )

    def handle(self, *args, **options):
        if options.get("base_dir"):
            base_dir = Path(options["base_dir"]).expanduser().resolve()
        else:
            base_dir = (
                Path(__file__)
                .resolve()
                .parents[2]
                / "data"
                / "esco"
                / "raw"
            )

        stats = import_esco_catalog(
            base_dir,
            batch_size=max(1, int(options.get("batch_size") or 1000)),
        )
        clear_esco_skill_index_cache()

        self.stdout.write(self.style.SUCCESS("ESCO catalog import completed."))
        for key, value in stats.as_dict().items():
            self.stdout.write(f"{key}: {value}")
