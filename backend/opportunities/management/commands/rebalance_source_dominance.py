from django.core.management.base import BaseCommand
from django.db.models import Count

from opportunities.models import Opportunite, StatutOpportunite


class Command(BaseCommand):
    help = (
        "Archive older active opportunities from a dominant source to enforce a "
        "dataset-level active cap and reduce source bias."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="MarchesPublics",
            help="Source name to rebalance (default: MarchesPublics).",
        )
        parser.add_argument(
            "--type-opportunite",
            default="PROJET",
            help="Opportunity type to rebalance (default: PROJET).",
        )
        parser.add_argument(
            "--max-active",
            type=int,
            default=1000,
            help="Maximum number of ACTIVE records to keep for the source/type.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the archival changes. Without this flag, run in dry-run mode.",
        )

    def handle(self, *args, **options):
        source_name = str(options["source"] or "").strip()
        type_opportunite = str(options["type_opportunite"] or "").strip()
        max_active = max(1, int(options["max_active"] or 1000))
        apply_changes = bool(options["apply"])

        active_queryset = Opportunite.objects.filter(
            source__nom=source_name,
            type_opportunite=type_opportunite,
            statut=StatutOpportunite.ACTIVE,
        ).order_by("-date_publication", "-id")

        active_count_before = active_queryset.count()
        keep_ids = list(active_queryset.values_list("id", flat=True)[:max_active])

        to_archive_queryset = active_queryset.exclude(id__in=keep_ids)
        to_archive_count = to_archive_queryset.count()

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"=== REBALANCE SOURCE DOMINANCE ({mode}) ===")
        self.stdout.write(f"source={source_name}")
        self.stdout.write(f"type_opportunite={type_opportunite}")
        self.stdout.write(f"max_active={max_active}")
        self.stdout.write(f"active_count_before={active_count_before}")
        self.stdout.write(f"to_archive={to_archive_count}")

        updated = 0
        if apply_changes and to_archive_count > 0:
            updated = to_archive_queryset.update(statut=StatutOpportunite.ARCHIVEE)

        active_count_after = Opportunite.objects.filter(
            source__nom=source_name,
            type_opportunite=type_opportunite,
            statut=StatutOpportunite.ACTIVE,
        ).count()

        total_active = Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE).count()
        top = (
            Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
            .values("source__nom")
            .annotate(c=Count("id"))
            .order_by("-c")
            .first()
        )
        top_ratio = (top["c"] / total_active) if top and total_active else 0.0

        if apply_changes:
            self.stdout.write(f"updated={updated}")
        self.stdout.write(f"active_count_after={active_count_after}")
        self.stdout.write(f"active_total={total_active}")
        self.stdout.write(f"top_source={top['source__nom'] if top else 'N/A'}")
        self.stdout.write(f"top_source_ratio={top_ratio:.4f}")
