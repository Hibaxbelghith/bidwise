from __future__ import annotations

import re
from typing import Any

from django.core.management.base import BaseCommand

from opportunities.autocomplete.service import normalize_profile_terms
from opportunities.models import ProfileSuggestionType
from users.models import Profil


LIST_SPLIT_RE = re.compile(r"\s*[,;|]\s*")


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = LIST_SPLIT_RE.split(value)
    else:
        return []

    cleaned = []
    for item in raw_items:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


class Command(BaseCommand):
    help = "Clean and canonicalize existing profile skill, target-role, and interest terms."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report cleanup statistics without writing profile updates.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of profiles to process and bulk-update per batch.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of profiles to scan.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        batch_size = max(1, int(options["batch_size"] or 500))
        limit = options.get("limit")

        queryset = Profil.objects.only(
            "id",
            "competences",
            "domaines_interet",
            "target_roles",
            "embedding",
            "embedding_features_hash",
            "last_embedding_update",
            "embedding_model",
            "embedding_dimensions",
            "embedding_updated_at",
            "embedding_content_hash",
        ).order_by("id")
        if limit is not None:
            queryset = queryset[: max(0, int(limit))]

        stats = {
            "dry_run": dry_run,
            "scanned": 0,
            "changed": 0,
            "skills_changed": 0,
            "interests_changed": 0,
            "roles_changed": 0,
            "skills_removed": 0,
            "interests_removed": 0,
            "roles_removed": 0,
        }
        pending_updates: list[Profil] = []

        def flush_updates() -> None:
            if dry_run or not pending_updates:
                pending_updates.clear()
                return

            Profil.objects.bulk_update(
                pending_updates,
                [
                    "competences",
                    "domaines_interet",
                    "target_roles",
                    "embedding",
                    "embedding_features_hash",
                    "last_embedding_update",
                    "embedding_model",
                    "embedding_dimensions",
                    "embedding_updated_at",
                    "embedding_content_hash",
                ],
                batch_size=batch_size,
            )
            pending_updates.clear()

        for profile in queryset.iterator(chunk_size=batch_size):
            stats["scanned"] += 1
            current_skills = _as_text_list(profile.competences)
            current_interests = _as_text_list(profile.domaines_interet)
            current_roles = _as_text_list(profile.target_roles)

            cleaned_skills = normalize_profile_terms(
                ProfileSuggestionType.SKILL,
                current_skills,
            )
            cleaned_interests = normalize_profile_terms(
                ProfileSuggestionType.INTEREST,
                current_interests,
                preserve_unknown=False,
            )
            cleaned_roles = normalize_profile_terms(
                ProfileSuggestionType.ROLE,
                current_roles,
                preserve_unknown_roles=True,
            )

            skills_changed = cleaned_skills != current_skills
            interests_changed = cleaned_interests != current_interests
            roles_changed = cleaned_roles != current_roles
            if not skills_changed and not interests_changed and not roles_changed:
                continue

            stats["changed"] += 1
            if skills_changed:
                stats["skills_changed"] += 1
                stats["skills_removed"] += max(0, len(current_skills) - len(cleaned_skills))
            if interests_changed:
                stats["interests_changed"] += 1
                stats["interests_removed"] += max(0, len(current_interests) - len(cleaned_interests))
            if roles_changed:
                stats["roles_changed"] += 1
                stats["roles_removed"] += max(0, len(current_roles) - len(cleaned_roles))

            if not dry_run:
                profile.competences = cleaned_skills
                profile.domaines_interet = cleaned_interests
                profile.target_roles = cleaned_roles
                profile.embedding = None
                profile.embedding_features_hash = ""
                profile.last_embedding_update = None
                profile.embedding_model = ""
                profile.embedding_dimensions = None
                profile.embedding_updated_at = None
                profile.embedding_content_hash = ""
                pending_updates.append(profile)
                if len(pending_updates) >= batch_size:
                    flush_updates()

        flush_updates()

        self.stdout.write(self.style.SUCCESS("Profile term cleanup complete"))
        for key in sorted(stats):
            self.stdout.write(f"{key}: {stats[key]}")
