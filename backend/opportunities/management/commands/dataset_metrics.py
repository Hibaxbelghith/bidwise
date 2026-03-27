import logging

from django.core.management.base import BaseCommand

from opportunities.dataset_metrics import compute_dataset_metrics


logger = logging.getLogger(__name__)


def _fmt_pct(value):
    return f"{value:.2f}%"


class Command(BaseCommand):
    help = "Compute dataset quality metrics before embedding generation."

    def handle(self, *args, **options):
        metrics = compute_dataset_metrics()

        self.stdout.write(self.style.SUCCESS("Dataset Quality Metrics"))
        self.stdout.write("=" * 60)

        self.stdout.write("\nSIZE")
        self.stdout.write(f"- Total records: {metrics['total']}")

        self.stdout.write("\nEMPTY")
        self.stdout.write(f"- Empty descriptions: {metrics['empty_description']}")
        self.stdout.write(f"- Empty titles: {metrics['empty_title']}")

        self.stdout.write("\nORG")
        self.stdout.write(
            f"- organization_nom coverage: {metrics['organization_non_empty']}/{metrics['total']} "
            f"({_fmt_pct(metrics['organization_rate'])})"
        )

        self.stdout.write("\nLENGTH (description)")
        self.stdout.write(f"- Average length: {metrics['avg_length']:.2f}")
        self.stdout.write(f"- Min length: {metrics['min_length']}")
        self.stdout.write(f"- Max length: {metrics['max_length']}")
        self.stdout.write("- Length buckets:")
        for bucket, count in metrics["length_buckets"].items():
            self.stdout.write(f"  - {bucket}: {count}")

        self.stdout.write("\nSTRUCTURE")
        self.stdout.write(
            f"- Records with 'contract:' or 'type:': {metrics['structured_count']}/{metrics['total']} "
            f"({_fmt_pct(metrics['structured_rate'])})"
        )

        self.stdout.write("\nTOP ORGANIZATIONS")
        if metrics["top_organizations"]:
            for row in metrics["top_organizations"]:
                self.stdout.write(f"- {row['name']}: {row['count']}")
        else:
            self.stdout.write("- No organization values found.")

        logger.info("Dataset metrics computed: %s", metrics)
