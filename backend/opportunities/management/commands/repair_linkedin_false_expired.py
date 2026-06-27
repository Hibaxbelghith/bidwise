from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from opportunities.models import Opportunite, StatutOpportunite


FALSE_CLOSE_SIGNALS = (
    "work closely",
    "collaborate closely",
    "close collaboration",
    "closely with",
)

EXPLICIT_CLOSED_SIGNALS = (
    "les candidatures ne sont plus accept",
    "applications are no longer accepted",
    "no longer accepting applications",
)


class Command(BaseCommand):
    help = (
        "Repair LinkedIn opportunities falsely expired by the old generic 'close' "
        "keyword rule. This does not reactivate explicit closed-application cases."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the repair. Without this flag, only prints the dry-run count.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1000,
            help="Maximum number of candidate opportunities to inspect.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options.get("apply"))
        limit = max(1, int(options.get("limit") or 1000))
        today = timezone.localdate()

        queryset = (
            Opportunite.objects
            .filter(source__nom__icontains="LinkedIn", statut=StatutOpportunite.EXPIREE)
            .filter(Q(date_limite__isnull=True) | Q(date_limite__gte=today))
            .filter(extra_data__expiration__reason__isnull=True)
            .order_by("-date_publication", "id")
        )

        inspected = 0
        repairable = []
        skipped_explicit_closed = 0

        for opportunity in queryset.iterator():
            if inspected >= limit:
                break
            inspected += 1

            blob = f"{opportunity.titre or ''} {opportunity.description or ''}".lower()
            if any(signal in blob for signal in EXPLICIT_CLOSED_SIGNALS):
                skipped_explicit_closed += 1
                continue
            if not any(signal in blob for signal in FALSE_CLOSE_SIGNALS):
                continue

            repairable.append(opportunity)

        if apply_changes:
            now_value = timezone.now()
            for opportunity in repairable:
                extra_data = dict(opportunity.extra_data or {})
                repair_history = list(extra_data.get("status_repair_history") or [])
                repair_history.append(
                    {
                        "repaired_on": today.isoformat(),
                        "reason": "linkedin_false_close_keyword",
                        "previous_status": StatutOpportunite.EXPIREE,
                        "next_status": StatutOpportunite.ACTIVE,
                    }
                )
                extra_data["status_repair_history"] = repair_history[-10:]
                opportunity.extra_data = extra_data
                opportunity.statut = StatutOpportunite.ACTIVE
                opportunity.date_modification = now_value
                opportunity.save(update_fields=["statut", "extra_data", "date_modification"])

        self.stdout.write(
            self.style.SUCCESS(
                "LinkedIn false-expired repair "
                f"mode={'apply' if apply_changes else 'dry-run'} "
                f"inspected={inspected} repairable={len(repairable)} "
                f"skipped_explicit_closed={skipped_explicit_closed}"
            )
        )
        if repairable:
            preview = ", ".join(str(item.id) for item in repairable[:20])
            suffix = "..." if len(repairable) > 20 else ""
            self.stdout.write(f"repairable_ids={preview}{suffix}")
