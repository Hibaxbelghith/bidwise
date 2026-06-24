from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ai.views import build_recommendations_for_user
from users.models import Profil, Utilisateur


class Command(BaseCommand):
    help = "Export BidWise recommendations to a CSV file ready for human evaluation."

    def add_arguments(self, parser):
        selector = parser.add_mutually_exclusive_group(required=True)
        selector.add_argument("--email", help="Candidate account email.")
        selector.add_argument("--profile-id", help="Candidate profile id.")
        parser.add_argument("--profile-slug", default="", help="Stable slug used in the evaluation dataset.")
        parser.add_argument("--top-k", type=int, default=25)
        parser.add_argument(
            "--output-csv",
            required=True,
            help="Output CSV path, relative to the backend container working directory or absolute.",
        )

    def handle(self, *args, **options):
        user = self._resolve_user(options)
        profile = user.profil
        top_k = max(1, min(int(options.get("top_k") or 25), 50))
        profile_slug = str(options.get("profile_slug") or "").strip() or f"profile_{profile.id}"
        output_path = Path(str(options["output_csv"]))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        recommendations = build_recommendations_for_user(user, limit=top_k)

        fieldnames = [
            "profile_slug",
            "profile_id",
            "profile_label",
            "rank",
            "opportunity_id",
            "title",
            "company",
            "source",
            "bidwise_score",
            "bidwise_bucket",
            "bidwise_confidence",
            "reason_summary",
            "human_label",
            "annotation_reason",
        ]

        with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for index, item in enumerate(recommendations, start=1):
                source = item.get("source") if isinstance(item.get("source"), dict) else {}
                reasons = item.get("reasons") or item.get("reason") or []
                if not isinstance(reasons, list):
                    reasons = [str(reasons)]
                writer.writerow(
                    {
                        "profile_slug": profile_slug,
                        "profile_id": profile.id,
                        "profile_label": self._profile_label(user),
                        "rank": index,
                        "opportunity_id": item.get("id") or "",
                        "title": item.get("title") or item.get("titre") or "",
                        "company": item.get("company") or item.get("organisation_nom") or "",
                        "source": source.get("nom") or item.get("source_name") or "",
                        "bidwise_score": item.get("score") or item.get("match_score") or 0,
                        "bidwise_bucket": item.get("recommendation_bucket") or "",
                        "bidwise_confidence": item.get("recommendation_confidence") or "",
                        "reason_summary": " | ".join(str(reason) for reason in reasons[:5]),
                        "human_label": "",
                        "annotation_reason": "",
                    }
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(recommendations)} recommendations for user_id={user.id} "
                f"profile_id={profile.id} to {output_path}"
            )
        )

    def _resolve_user(self, options):
        email = str(options.get("email") or "").strip()
        if email:
            try:
                return Utilisateur.objects.select_related("profil").get(email__iexact=email)
            except Utilisateur.DoesNotExist as exc:
                raise CommandError(f"No user found for email: {email}") from exc

        profile_id = str(options.get("profile_id") or "").strip()
        try:
            profile = Profil.objects.select_related("utilisateur").get(pk=int(profile_id))
        except (TypeError, ValueError, Profil.DoesNotExist) as exc:
            raise CommandError(f"No profile found for id: {profile_id}") from exc
        return profile.utilisateur

    def _profile_label(self, user):
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        return full_name or user.email or f"Profil #{user.profil.id}"
