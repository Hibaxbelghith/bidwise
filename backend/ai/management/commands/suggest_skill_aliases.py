import json

from django.core.management.base import BaseCommand, CommandError

from ai.skill_alias_suggestions import (
    TARGET_ALL,
    VALID_TARGETS,
    build_skill_alias_suggestions,
    summarize_skill_alias_suggestions,
    write_skill_alias_suggestions_csv,
)


class Command(BaseCommand):
    help = (
        "Suggest candidate BidWise skill aliases by mining frequent unmatched skills "
        "from opportunities, profiles, and resumes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            choices=sorted(VALID_TARGETS),
            default=TARGET_ALL,
            help="Entity family to inspect.",
        )
        parser.add_argument(
            "--top-n",
            type=int,
            default=200,
            help="Maximum number of unmatched skill candidates to return after aggregation.",
        )
        parser.add_argument(
            "--min-count",
            type=int,
            default=2,
            help="Minimum aggregated frequency required for a suggestion to appear.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Safe scan window size while iterating historical rows.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of rows to scan per selected target.",
        )
        parser.add_argument(
            "--semantic-candidate-limit",
            type=int,
            default=3,
            help="How many nearest ESCO candidates to inspect when building semantic review hints.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Optional CSV output path for review.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the suggestion payload as JSON.",
        )

    def handle(self, *args, **options):
        top_n = max(0, int(options["top_n"] or 0))
        min_count = max(1, int(options["min_count"] or 1))
        batch_size = max(1, int(options["batch_size"] or 200))
        scan_limit = options.get("limit")
        semantic_candidate_limit = max(1, int(options["semantic_candidate_limit"] or 3))
        target = str(options["target"] or TARGET_ALL)

        if scan_limit is not None and int(scan_limit) < 0:
            raise CommandError("--limit must be >= 0")

        suggestions = build_skill_alias_suggestions(
            target=target,
            top_n=top_n,
            min_count=min_count,
            chunk_size=batch_size,
            scan_limit=scan_limit,
            semantic_candidate_limit=semantic_candidate_limit,
        )
        summary = summarize_skill_alias_suggestions(suggestions)

        output_path = options.get("output")
        if output_path:
            written_path = write_skill_alias_suggestions_csv(output_path, suggestions)
            self.stdout.write(self.style.SUCCESS(f"Wrote alias review CSV: {written_path}"))

        if bool(options["json"]):
            payload = {
                "summary": summary,
                "suggestions": [item.as_dict() for item in suggestions],
            }
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return

        self.stdout.write(self.style.SUCCESS("Skill alias suggestions generated"))
        self.stdout.write(
            "Summary: total=%s actions=%s"
            % (
                summary["total_suggestions"],
                summary["action_breakdown"],
            )
        )
        for suggestion in suggestions[:20]:
            self.stdout.write(
                "- %s | count=%s | action=%s | candidate=%s | score=%s"
                % (
                    suggestion.raw_skill,
                    suggestion.total_count,
                    suggestion.recommended_action,
                    suggestion.top_candidate_label or "",
                    suggestion.top_candidate_similarity if suggestion.top_candidate_similarity is not None else "",
                )
            )

