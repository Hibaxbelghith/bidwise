from django.core.management.base import BaseCommand

from opportunities.autocomplete.indexer import build_profile_suggestion_index


class Command(BaseCommand):
    help = "Rebuild opportunity-derived profile skill, role, and interest autocomplete suggestions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Extract and aggregate suggestions without writing to the database.",
        )
        parser.add_argument(
            "--min-skill-frequency",
            type=int,
            default=2,
            help="Minimum opportunity count required for a skill suggestion.",
        )
        parser.add_argument(
            "--min-role-frequency",
            type=int,
            default=2,
            help="Minimum opportunity count required for a role suggestion.",
        )
        parser.add_argument(
            "--min-interest-frequency",
            type=int,
            default=1,
            help="Minimum opportunity count required for an industry/interest suggestion.",
        )

    def handle(self, *args, **options):
        result = build_profile_suggestion_index(
            dry_run=options["dry_run"],
            min_frequency={
                "SKILL": max(1, options["min_skill_frequency"]),
                "ROLE": max(1, options["min_role_frequency"]),
                "INTEREST": max(1, options["min_interest_frequency"]),
            },
        )
        self.stdout.write(self.style.SUCCESS("Profile autocomplete rebuild complete"))
        for key in sorted(result):
            self.stdout.write(f"{key}: {result[key]}")
