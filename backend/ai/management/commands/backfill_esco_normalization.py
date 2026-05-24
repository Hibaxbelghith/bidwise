import json

from django.core.management.base import BaseCommand, CommandError

from ai.esco_normalization_recovery import (
    TARGET_ALL,
    VALID_TARGETS,
    backfill_esco_normalization,
)


class Command(BaseCommand):
    help = "Backfill missing ESCO normalized skill storage for opportunities, profiles, and parsed resumes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=sorted(VALID_TARGETS),
            default=TARGET_ALL,
            help="Entity family to backfill.",
        )
        parser.add_argument(
            "--resume-mode",
            choices=["full", "candidate_cleanup"],
            default="full",
            help=(
                "Resume backfill strategy. "
                "'full' reruns semantic extraction and normalization; "
                "'candidate_cleanup' reuses stored resume candidates and only refreshes "
                "the ESCO normalization payload plus rejected-candidate analytics."
            ),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
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
            help="Optional primary-key lower bound to resume a previous backfill run.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recompute normalization even when the stored content hash is already fresh.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the final summary as JSON.",
        )

    def handle(self, *args, **options):
        batch_size = max(1, int(options["batch_size"] or 100))
        limit = options.get("limit")
        start_after_id = options.get("from_id")
        target = str(options["target"] or TARGET_ALL)
        emit_json = bool(options["json"])
        resume_mode = str(options.get("resume_mode") or "full")

        if limit is not None and int(limit) < 0:
            raise CommandError("--limit must be >= 0")
        if start_after_id is not None and int(start_after_id) < 0:
            raise CommandError("--from-id must be >= 0")

        last_scanned = {}

        def on_progress(stats):
            previous = last_scanned.get(stats.target)
            if previous == stats.scanned:
                return
            last_scanned[stats.target] = stats.scanned
            self.stdout.write(
                "[%s] scanned=%s eligible=%s updated=%s skipped_fresh=%s failed=%s last_id=%s"
                % (
                    stats.target,
                    stats.scanned,
                    stats.eligible,
                    stats.updated,
                    stats.skipped_already_normalized,
                    stats.failed,
                    stats.last_processed_id,
                )
            )

        summary = backfill_esco_normalization(
            target=target,
            chunk_size=batch_size,
            limit=limit,
            force=bool(options["force"]),
            start_after_id=start_after_id,
            resume_mode=resume_mode,
            progress_callback=on_progress,
        )

        if emit_json:
            self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
            return

        self.stdout.write(self.style.SUCCESS("ESCO normalization backfill complete"))
        for key, payload in summary.items():
            self.stdout.write(f"[{key}]")
            for metric_name, metric_value in payload.items():
                self.stdout.write(f"  {metric_name}: {metric_value}")
