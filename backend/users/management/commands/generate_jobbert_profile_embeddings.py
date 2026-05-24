from __future__ import annotations

from django.core.management.base import BaseCommand

from ai.jobbert import get_or_build_profile_jobbert_embedding, jobbert_model_name
from ai.user_features import build_user_features
from users.models import Profil


class Command(BaseCommand):
    help = "Generate cached JobBERT embeddings for candidate profiles."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        limit = max(1, min(int(options.get("limit") or 100), 1000))
        force = bool(options.get("force"))
        model_name = jobbert_model_name()

        queryset = (
            Profil.objects
            .select_related("utilisateur")
            .prefetch_related("resumes")
            .order_by("-id")
        )
        if not force:
            queryset = queryset.exclude(jobbert_embedding__isnull=False, jobbert_embedding_model=model_name)

        updated = 0
        skipped = 0
        errors = 0
        for profile in queryset[:limit]:
            if force:
                profile.jobbert_embedding = None
                profile.jobbert_embedding_model = ""
                profile.jobbert_embedding_content_hash = ""
            try:
                vector = get_or_build_profile_jobbert_embedding(profile, build_user_features(profile))
            except Exception as exc:  # noqa: BLE001 - batch command should continue
                errors += 1
                self.stderr.write(f"Profile {profile.pk} failed: {exc}")
                continue
            if vector:
                updated += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS("JobBERT profile embeddings completed."))
        self.stdout.write(f"Model: {model_name}")
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Errors: {errors}")
