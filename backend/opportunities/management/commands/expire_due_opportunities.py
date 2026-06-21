from django.core.management.base import BaseCommand

from opportunities.organization_expiration import expire_due_opportunities


class Command(BaseCommand):
    help = "Expire ACTIVE opportunities whose deadline is already in the past."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type-opportunite",
            default="",
            help="Optional opportunity type filter, for example PROJET or EMPLOI. Default: all types.",
        )
        parser.add_argument(
            "--source",
            default="",
            help="Optional source name filter, for example MarchesPublics.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the changes. Without this flag, run in dry-run mode.",
        )

    def handle(self, *args, **options):
        result = expire_due_opportunities(
            type_opportunite=str(options["type_opportunite"] or "").strip() or None,
            source_name=str(options["source"] or "").strip() or None,
            apply_changes=bool(options["apply"]),
        )

        self.stdout.write(f"date={result['date']}")
        self.stdout.write(f"mode={result['mode']}")
        self.stdout.write(f"filters={result['filters']}")
        self.stdout.write(f"inspected={result['inspected']}")
        self.stdout.write(f"expired={result['expired']}")
        if result["expired_ids"]:
            preview = result["expired_ids"][:20]
            suffix = "..." if len(result["expired_ids"]) > len(preview) else ""
            self.stdout.write(f"expired_ids={preview}{suffix}")
