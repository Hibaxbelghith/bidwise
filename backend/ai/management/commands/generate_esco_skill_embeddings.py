from django.db.models import Q
from django.utils import timezone

from django.core.management.base import BaseCommand, CommandError

from ai.esco_skill_embeddings import (
    ESCOSkillEmbeddingValidationError,
    build_embedding_metadata,
    embedding_metadata_is_complete,
    embedding_model_matches,
    validate_embedding_shape,
)
from ai.esco_skill_index import build_esco_skill_embedding_text, clear_esco_skill_index_cache
from ai.models import ESCOSkill
from opportunities.embeddings import service


class Command(BaseCommand):
    help = "Generate and persist ESCO skill embeddings using the shared project embedding stack."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            default=None,
            help="Embedding model name. If omitted, OPPORTUNITY_EMBEDDING_MODEL is used.",
        )
        parser.add_argument(
            "--model-version",
            default=None,
            help="Optional model version tag stored with ESCO skill embeddings.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing ESCO skill embeddings.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of skills processed.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=service.DEFAULT_BATCH_SIZE,
            help="Batch size for model.encode(list_of_texts).",
        )

    def handle(self, *args, **options):
        try:
            metadata = build_embedding_metadata(
                model_name=options.get("model"),
                model_version=options.get("model_version"),
            )
        except (ValueError, ESCOSkillEmbeddingValidationError) as exc:
            raise CommandError(str(exc))
        model_name = metadata["model_name"]
        model_version = metadata["model_version"]
        expected_dimensions = metadata["dimensions"]
        model_identifier = metadata["identifier"]

        force = bool(options.get("force"))
        batch_size = max(1, int(options.get("batch_size") or service.DEFAULT_BATCH_SIZE))
        limit = options.get("limit")

        queryset = ESCOSkill.objects.all().order_by("id")
        if not force:
            conflict_queryset = queryset.filter(
                embedding__isnull=False,
            ).filter(
                ~Q(embedding_model=""),
                ~Q(embedding_version=""),
                Q(embedding_dimensions__isnull=False),
                Q(embedding_updated_at__isnull=False),
            ).filter(
                ~Q(embedding_model=model_name)
                | ~Q(embedding_version=model_version)
                | ~Q(embedding_dimensions=expected_dimensions)
            )
            conflict_count = conflict_queryset.count()
            if conflict_count:
                raise CommandError(
                    "Refusing to overwrite existing ESCO skill embeddings with different "
                    f"metadata (count={conflict_count}, target={model_identifier}, "
                    "use --force to overwrite)."
                )
            queryset = queryset.filter(
                Q(embedding__isnull=True)
                | Q(embedding_model="")
                | Q(embedding_version="")
                | Q(embedding_dimensions__isnull=True)
                | Q(embedding_updated_at__isnull=True)
            )
        if limit:
            queryset = queryset[:limit]

        skills = list(queryset)
        total = len(skills)
        if total == 0:
            self.stdout.write("No ESCO skills to process.")
            return

        self.stdout.write(
            f"Generating ESCO skill embeddings using model='{model_identifier}' "
            f"(force={force}, total={total}, batch_size={batch_size})"
        )

        updated = 0
        skipped = 0
        errors = 0

        for start in range(0, total, batch_size):
            batch = skills[start:start + batch_size]
            text_payload = []
            target_rows = []

            for skill in batch:
                text = build_esco_skill_embedding_text(
                    skill.preferred_label,
                    skill.alt_labels,
                    preferred_label_en=skill.preferred_label_en,
                    preferred_label_fr=skill.preferred_label_fr,
                    alt_labels_en=skill.alt_labels_en,
                    alt_labels_fr=skill.alt_labels_fr,
                    hidden_labels_en=skill.hidden_labels_en,
                    hidden_labels_fr=skill.hidden_labels_fr,
                    search_text_multilingual=skill.search_text_multilingual,
                )
                if not text:
                    skipped += 1
                    continue
                text_payload.append(text)
                target_rows.append(skill)

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
                self.stderr.write(f"Batch embedding generation failed: {exc}")
                continue
            if len(vectors) != len(target_rows):
                raise CommandError(
                    "Embedding generation returned an unexpected number of vectors "
                    f"(expected={len(target_rows)}, got={len(vectors)})."
                )

            rows_to_update = []
            current_time = timezone.now()
            for skill, vector in zip(target_rows, vectors):
                try:
                    payload = validate_embedding_shape(
                        vector,
                        expected_dimensions=expected_dimensions,
                    )
                except ESCOSkillEmbeddingValidationError as exc:
                    raise CommandError(
                        f"Invalid embedding generated for ESCOSkill(uri={skill.uri}): {exc}"
                    ) from exc

                if (
                    getattr(skill, "embedding", None) is not None
                    and not force
                    and embedding_metadata_is_complete(skill)
                    and not embedding_model_matches(
                    skill,
                    model_name,
                    model_version=model_version,
                    expected_dimensions=expected_dimensions,
                    )
                ):
                    raise CommandError(
                        "Refusing to overwrite an ESCO skill embedding with different metadata "
                        f"without --force (uri={skill.uri}, target={model_identifier})."
                    )

                skill.embedding = payload
                skill.embedding_model = model_name
                skill.embedding_dimensions = len(payload)
                skill.embedding_version = model_version
                skill.embedding_updated_at = current_time
                rows_to_update.append(skill)

            if rows_to_update:
                ESCOSkill.objects.bulk_update(
                    rows_to_update,
                    fields=[
                        "embedding",
                        "embedding_model",
                        "embedding_dimensions",
                        "embedding_version",
                        "embedding_updated_at",
                    ],
                    batch_size=batch_size,
                )
                updated += len(rows_to_update)

            processed = min(start + batch_size, total)
            self.stdout.write(f"Processed {processed}/{total}...")

        clear_esco_skill_index_cache()
        self.stdout.write(self.style.SUCCESS("ESCO skill embedding generation completed."))
        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Skipped: {skipped}")
        self.stdout.write(f"Errors: {errors}")
