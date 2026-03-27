from django.core.management.base import BaseCommand
from django.db.models import Count

from opportunities.embeddings import service
from opportunities.models import Opportunite


class Command(BaseCommand):
    help = "Show embeddings coverage and model/version distribution."

    @staticmethod
    def _pct(part, total):
        if total <= 0:
            return 0.0
        return (part / total) * 100.0

    def handle(self, *args, **options):
        total = Opportunite.objects.count()
        with_embeddings = Opportunite.objects.exclude(embedding_vector__isnull=True).count()
        without_embeddings = max(total - with_embeddings, 0)

        production_identifier = service.build_embedding_model_identifier()
        production_count = (
            Opportunite.objects.exclude(embedding_vector__isnull=True)
            .filter(embedding_model=production_identifier)
            .count()
        )

        by_model = list(
            Opportunite.objects.exclude(embedding_vector__isnull=True)
            .values("embedding_model")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        active_identifier = by_model[0]["embedding_model"] if by_model else ""

        self.stdout.write("Embeddings Status")
        self.stdout.write("-" * 60)
        self.stdout.write(f"Total opportunities: {total}")
        self.stdout.write(
            "Coverage: {} ({:.2f}%)".format(
                with_embeddings,
                self._pct(with_embeddings, total),
            )
        )
        self.stdout.write(
            "Missing embeddings: {} ({:.2f}%)".format(
                without_embeddings,
                self._pct(without_embeddings, total),
            )
        )
        self.stdout.write(f"Configured production model: {production_identifier}")
        self.stdout.write(
            "Production-tagged records: {} ({:.2f}% of dataset)".format(
                production_count,
                self._pct(production_count, total),
            )
        )
        self.stdout.write(f"Most present model in DB: {active_identifier or 'N/A'}")

        if by_model:
            self.stdout.write("")
            self.stdout.write("Model distribution:")
            for row in by_model:
                label = row["embedding_model"] or "<empty>"
                self.stdout.write(
                    "- {}: {} ({:.2f}% of dataset)".format(
                        label,
                        row["total"],
                        self._pct(row["total"], total),
                    )
                )
