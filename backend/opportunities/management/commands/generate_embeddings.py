import logging

from django.core.management.base import BaseCommand, CommandError

from opportunities.embeddings import service
from opportunities.models import Opportunite
from opportunities.nlp_preprocessing import prepare_combined_text


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate and persist opportunity embeddings for a selected model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            default=None,
            help="Embedding model name. If omitted, OPPORTUNITY_EMBEDDING_MODEL is used.",
        )
        parser.add_argument(
            "--model-version",
            default=None,
            help="Optional model version tag stored with embeddings (example: v1, 2026-03).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing embeddings.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of opportunities processed.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=service.DEFAULT_BATCH_SIZE,
            help="Batch size for model.encode(list_of_texts).",
        )

    def handle(self, *args, **options):
        try:
            model_name = service.resolve_model_name(options.get("model"))
        except ValueError as exc:
            raise CommandError(str(exc))
        model_identifier = service.build_embedding_model_identifier(
            model_name=model_name,
            model_version=options.get("model_version"),
        )

        force = bool(options.get("force"))
        batch_size = max(1, int(options.get("batch_size") or service.DEFAULT_BATCH_SIZE))
        limit = options.get("limit")

        queryset = Opportunite.objects.all().order_by("id")
        if not force:
            same_model_count = queryset.exclude(embedding_vector__isnull=True).filter(
                embedding_model=model_identifier
            ).count()
            other_model_count = queryset.exclude(embedding_vector__isnull=True).exclude(
                embedding_model=model_identifier
            ).count()
            self.stdout.write(
                "Idempotent mode: existing same_model={} | existing other_model={} "
                "(use --force to overwrite)".format(same_model_count, other_model_count)
            )
            queryset = queryset.filter(embedding_vector__isnull=True)
        if limit:
            queryset = queryset[:limit]

        opportunities = list(queryset)
        total = len(opportunities)
        if total == 0:
            self.stdout.write("No opportunities to process.")
            return

        self.stdout.write(
            f"Generating embeddings using model='{model_identifier}' "
            f"(force={force}, total={total}, batch_size={batch_size})"
        )

        updated = 0
        skipped = 0
        errors = 0

        for start in range(0, total, batch_size):
            batch = opportunities[start:start + batch_size]
            text_payload = []
            target_rows = []

            for opportunity in batch:
                if not force and opportunity.embedding_vector:
                    skipped += 1
                    continue

                combined_text = prepare_combined_text(opportunity)
                if not combined_text:
                    skipped += 1
                    continue

                text_payload.append(combined_text)
                target_rows.append(opportunity)

            if not text_payload:
                continue

            try:
                vectors = service.generate_embeddings_batch(
                    text_payload,
                    model_name=model_name,
                    batch_size=batch_size,
                )
            except Exception as exc:  # noqa: BLE001 - keep command resilient
                errors += len(target_rows)
                logger.exception("Batch embedding generation failed: %s", exc)
                continue

            rows_to_update = []
            for opportunity, vector in zip(target_rows, vectors):
                if not vector:
                    skipped += 1
                    continue
                opportunity.embedding_vector = vector
                opportunity.embedding_model = model_identifier
                rows_to_update.append(opportunity)

            if rows_to_update:
                Opportunite.objects.bulk_update(
                    rows_to_update,
                    fields=["embedding_vector", "embedding_model"],
                    batch_size=batch_size,
                )
                updated += len(rows_to_update)

            processed = min(start + batch_size, total)
            self.stdout.write(f"Processed {processed}/{total}...")

        self.stdout.write(self.style.SUCCESS("Embeddings generation completed."))
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Errors: {errors}")
