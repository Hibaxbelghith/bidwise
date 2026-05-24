import json
from pathlib import Path

from django.core.management.base import BaseCommand

from ai.models import ESCOOccupation


class Command(BaseCommand):
    help = "Load lightweight ESCO occupations and skills dataset"

    def handle(self, *args, **options):
        self.stdout.write("Loading ESCO dataset...")

        data_path = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "data"
            / "esco_occupations.json"
        )

        with open(data_path, "r", encoding="utf-8") as f:
            occupations = json.load(f)

        created_count = 0

        for item in occupations:
            _, created = ESCOOccupation.objects.get_or_create(
                uri=item["uri"],
                defaults={
                    "preferred_label": item["preferred_label"],
                    "family": item["family"],
                    "isco_group": item["isco_group"],
                    "alternate_labels": item["alternate_labels"],
                    "related_skills": item["related_skills"],
                },
            )

            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {created_count} ESCO occupations"
            )
        )