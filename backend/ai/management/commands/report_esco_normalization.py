import json

from django.core.management.base import BaseCommand, CommandError

from ai.esco_normalization_recovery import (
    TARGET_ALL,
    VALID_TARGETS,
    build_esco_normalization_report,
)


class Command(BaseCommand):
    help = "Report ESCO normalization coverage, pending backlog, and top matched/unmatched skills."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=sorted(VALID_TARGETS),
            default=TARGET_ALL,
            help="Entity family to inspect.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Window size used to iterate database rows safely.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of rows to scan per target.",
        )
        parser.add_argument(
            "--from-id",
            type=int,
            default=None,
            help="Optional primary-key lower bound for partial audits.",
        )
        parser.add_argument(
            "--top-n",
            type=int,
            default=10,
            help="How many matched/unmatched skills to include in the report.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the report as JSON.",
        )

    def handle(self, *args, **options):
        batch_size = max(1, int(options["batch_size"] or 200))
        limit = options.get("limit")
        start_after_id = options.get("from_id")
        top_n = max(1, int(options["top_n"] or 10))
        target = str(options["target"] or TARGET_ALL)

        if limit is not None and int(limit) < 0:
            raise CommandError("--limit must be >= 0")
        if start_after_id is not None and int(start_after_id) < 0:
            raise CommandError("--from-id must be >= 0")

        report = build_esco_normalization_report(
            target=target,
            chunk_size=batch_size,
            limit=limit,
            start_after_id=start_after_id,
            top_n=top_n,
        )

        if bool(options["json"]):
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            return

        self.stdout.write(self.style.SUCCESS("ESCO normalization coverage report"))
        for key, payload in report.items():
            self.stdout.write(f"[{key}]")
            for metric_name, metric_value in payload.items():
                self.stdout.write(f"  {metric_name}: {metric_value}")
