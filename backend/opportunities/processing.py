import logging
import math
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from opportunities.models import (
    Opportunite,
    RawOpportunite,
    RawOpportuniteProcessingStatus,
    StatutOpportunite,
)
from opportunities.embeddings.service import (
    build_embedding_model_identifier,
    generate_opportunity_embedding,
)
from opportunities.enrichment import enrich_opportunity_text
from opportunities.materialization import materialize_opportunity
from opportunities.normalization import normalize_raw_opportunity
from opportunities.quality.quality_gate import evaluate_opportunity


logger = logging.getLogger(__name__)


def _to_pgvector_payload(vector: Any) -> list[float] | None:
    if not isinstance(vector, list) or not vector:
        return None

    expected_dimensions = int(getattr(settings, "OPPORTUNITY_PGVECTOR_DIMENSIONS", 384))
    if len(vector) != expected_dimensions:
        return None

    casted: list[float] = []
    try:
        for item in vector:
            value = float(item)
            if not math.isfinite(value):
                return None
            casted.append(value)
    except (TypeError, ValueError):
        return None

    return casted


def _append_validation_error(existing_errors: Any, new_error: str) -> list[str]:
    errors = existing_errors if isinstance(existing_errors, list) else []
    return [*errors, new_error]


def _pgvector_equals(existing: Any, incoming: list[float] | None) -> bool:
    if incoming is None:
        return existing is None
    if existing is None:
        return False

    try:
        existing_values = [float(item) for item in existing]
    except (TypeError, ValueError):
        return False

    if len(existing_values) != len(incoming):
        return False

    return all(abs(a - b) <= 1e-12 for a, b in zip(existing_values, incoming))


def _inline_embeddings_enabled() -> bool:
    return bool(getattr(settings, "OPPORTUNITY_INLINE_EMBEDDINGS_ENABLED", False))


def _update_opportunity_embedding(opportunity: Opportunite, *, raw_id: int) -> None:
    try:
        embedding_vector = generate_opportunity_embedding(opportunity)
        embedding_model = build_embedding_model_identifier()
        embedding_vector_pg = _to_pgvector_payload(embedding_vector)

        opportunity_update_fields = []
        if opportunity.embedding_vector != embedding_vector:
            opportunity.embedding_vector = embedding_vector
            opportunity_update_fields.append("embedding_vector")
        if opportunity.embedding_model != embedding_model:
            opportunity.embedding_model = embedding_model
            opportunity_update_fields.append("embedding_model")
        if not _pgvector_equals(opportunity.embedding_vector_pg, embedding_vector_pg):
            opportunity.embedding_vector_pg = embedding_vector_pg
            opportunity_update_fields.append("embedding_vector_pg")

        if opportunity_update_fields:
            opportunity.save(update_fields=opportunity_update_fields)
    except Exception:
        logger.exception(
            "Embedding generation failed raw_id=%s opportunity_id=%s",
            raw_id,
            opportunity.pk,
        )


def _reject_raw_opportunity(raw_obj: RawOpportunite, error_message: str) -> None:
    """
    Mark one raw record as REJECTED without deleting any data.

    Safety rules:
    - Never downgrade VALIDATED/MATERIALIZED.
    - Never overwrite processed_at if it already exists.
    - Always append validation errors (do not replace history).
    """

    with transaction.atomic():
        raw_obj = RawOpportunite.objects.select_for_update().get(pk=raw_obj.pk)

        if raw_obj.processing_status in (
            RawOpportuniteProcessingStatus.VALIDATED,
            RawOpportuniteProcessingStatus.MATERIALIZED,
        ):
            logger.warning(
                "Skipping rejection to avoid status overwrite raw_id=%s current_status=%s error=%s",
                raw_obj.pk,
                raw_obj.processing_status,
                error_message,
            )
            return

        update_fields = ["validation_errors"]
        raw_obj.validation_errors = _append_validation_error(raw_obj.validation_errors, error_message)

        if raw_obj.processing_status == RawOpportuniteProcessingStatus.NEW:
            raw_obj.processing_status = RawOpportuniteProcessingStatus.REJECTED
            update_fields.append("processing_status")

        if raw_obj.processed_at is None:
            raw_obj.processed_at = timezone.now()
            update_fields.append("processed_at")

        raw_obj.save(update_fields=update_fields)


def process_raw_opportunity(raw_obj: RawOpportunite) -> Opportunite | None:
    """
    Orchestrate RAW -> CANONICAL -> MATERIALIZED for one RawOpportunite.

    Flow:
    1) normalize_raw_opportunity(raw_obj)
    2) materialize_opportunity(normalized_data)
    3) update RawOpportunite status/link safely

    Notes:
    - NLP is intentionally not part of this layer.
    - This function catches ValueError from normalization/materialization and
      marks the raw record as REJECTED instead of crashing the pipeline.
    """

    if raw_obj.pk is None:
        logger.warning("Cannot process unsaved RawOpportunite instance")
        return None

    raw_id = raw_obj.pk

    try:
        # Keep canonical write + raw state transition in one DB transaction.
        with transaction.atomic():
            locked_raw = RawOpportunite.objects.select_for_update().get(pk=raw_id)

            # Step 4 only transitions NEW records. Other states are preserved.
            if locked_raw.processing_status != RawOpportuniteProcessingStatus.NEW:
                logger.info(
                    "Skipping raw processing raw_id=%s current_status=%s",
                    raw_id,
                    locked_raw.processing_status,
                )
                return locked_raw.canonical

            # Pipeline flow:
            # 1. normalization: map raw structured data
            # 2. enrichment: extract derived fields from text
            # 3. scoring: evaluate quality
            # 4. materialization: persist to DB
            normalized_data = normalize_raw_opportunity(locked_raw)
            normalized_data.update(enrich_opportunity_text(normalized_data))
            normalized_data = evaluate_opportunity(normalized_data)
            if not normalized_data.get("is_usable", True):
                reason = normalized_data.get("unusable_reason") or "quality_gate_rejected"
                raise ValueError(f"Quality gate rejected record: {reason}")
            opportunity = materialize_opportunity(normalized_data)
            previous_canonical_id = locked_raw.canonical_id

            update_fields: list[str] = []

            locked_raw.processing_status = RawOpportuniteProcessingStatus.MATERIALIZED
            update_fields.append("processing_status")

            # Keep raw linkage aligned with the latest canonical result.
            if locked_raw.canonical_id != opportunity.id:
                locked_raw.canonical = opportunity
                update_fields.append("canonical")

            # Never overwrite processed_at if already set.
            if locked_raw.processed_at is None:
                locked_raw.processed_at = timezone.now()
                update_fields.append("processed_at")

            locked_raw.save(update_fields=update_fields)

            from ai.tasks import enqueue_opportunity_skill_normalization

            transaction.on_commit(
                lambda opportunity_id=opportunity.pk: enqueue_opportunity_skill_normalization(
                    opportunity_id
                )
            )

            # If date/type correction moved this raw snapshot to a different
            # canonical row, archive the previous orphan active row to avoid
            # user-facing duplicates caused by fallback values.
            if previous_canonical_id and previous_canonical_id != opportunity.id:
                previous = Opportunite.objects.select_for_update().filter(pk=previous_canonical_id).first()
                if previous and previous.titre == opportunity.titre and previous.source_id == opportunity.source_id:
                    still_linked = RawOpportunite.objects.filter(canonical_id=previous.pk).exists()
                    if not still_linked and previous.statut == StatutOpportunite.ACTIVE:
                        previous.statut = StatutOpportunite.ARCHIVEE
                        previous.save(update_fields=["statut"])

        logger.info(
            "Raw materialization succeeded raw_id=%s opportunity_id=%s",
            raw_id,
            opportunity.pk,
        )
        if _inline_embeddings_enabled():
            _update_opportunity_embedding(opportunity, raw_id=raw_id)
        return opportunity

    except ValueError as exc:
        error_message = str(exc)

        try:
            _reject_raw_opportunity(raw_obj, error_message)
        except Exception:
            logger.exception(
                "Failed to persist rejection state raw_id=%s error=%s",
                raw_id,
                error_message,
            )

        logger.warning(
            "Raw materialization failed raw_id=%s error=%s",
            raw_id,
            error_message,
        )
        return None

    except Exception as exc:  # noqa: BLE001 - keep per-record pipeline resilient
        error_message = f"Unexpected processing error: {exc}"

        try:
            _reject_raw_opportunity(raw_obj, error_message)
        except Exception:
            logger.exception(
                "Failed to persist unexpected rejection state raw_id=%s error=%s",
                raw_id,
                error_message,
            )

        logger.exception(
            "Raw processing crashed raw_id=%s error=%s",
            raw_id,
            error_message,
        )
        return None


def process_pending_raw_opportunities(limit: int = 100) -> dict:
    """
    Process a batch of pending raw opportunities (status=NEW).

    Batch policy:
    - deterministic ordering by id ASC
    - bounded by `limit`
    - per-item isolation: one failure must not stop the loop
    """

    stats = {
        "processed": 0,
        "created": 0,
        "updated": 0,
        "materialized": 0,
        "rejected": 0,
        "errors": 0,
        "failed": 0,
    }

    if limit <= 0:
        logger.info("Batch processing completed: %s", stats)
        return stats

    pending_raw_objects = list(
        RawOpportunite.objects
        .filter(processing_status=RawOpportuniteProcessingStatus.NEW)
        .order_by("id")[:limit]
    )

    logger.info("Starting batch processing limit=%s", limit)

    for raw_obj in pending_raw_objects:
        stats["processed"] += 1

        try:
            opportunity = process_raw_opportunity(raw_obj)

            if opportunity is None:
                stats["rejected"] += 1
                stats["failed"] += 1
            else:
                stats["materialized"] += 1
                if getattr(opportunity, "_materialization_created", False):
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

        except Exception:
            logger.exception("Batch unexpected error raw_id=%s", raw_obj.pk)
            stats["errors"] += 1
            stats["failed"] += 1

    logger.info("Batch processing completed: %s", stats)
    return stats
