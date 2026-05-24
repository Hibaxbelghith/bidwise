from __future__ import annotations

import math

from django.conf import settings

from opportunities.embeddings import service as embedding_service


class ESCOSkillEmbeddingValidationError(ValueError):
    """Raised when an ESCO skill embedding or its metadata is invalid."""


def get_expected_embedding_dimensions(expected_dimensions: int | None = None) -> int:
    if expected_dimensions is not None:
        value = expected_dimensions
    else:
        value = getattr(settings, "OPPORTUNITY_PGVECTOR_DIMENSIONS", 384)
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ESCOSkillEmbeddingValidationError(
            f"Invalid expected embedding dimensions '{value}'."
        ) from exc
    if resolved <= 0:
        raise ESCOSkillEmbeddingValidationError(
            f"Expected embedding dimensions must be positive, got {resolved}."
        )
    return resolved


def resolve_embedding_model_name(model_name: str | None = None) -> str:
    return embedding_service.resolve_model_name(model_name)


def resolve_embedding_version(model_version: str | None = None) -> str:
    return embedding_service.resolve_model_version(model_version)


def build_embedding_metadata(
    *,
    model_name: str | None = None,
    model_version: str | None = None,
    dimensions: int | None = None,
) -> dict[str, object]:
    resolved_model = resolve_embedding_model_name(model_name)
    resolved_version = resolve_embedding_version(model_version)
    resolved_dimensions = get_expected_embedding_dimensions(dimensions)
    return {
        "model_name": resolved_model,
        "model_version": resolved_version,
        "dimensions": resolved_dimensions,
        "identifier": embedding_service.build_embedding_model_identifier(
            model_name=resolved_model,
            model_version=resolved_version,
        ),
    }


def _coerce_vector_values(vector) -> list[float]:
    if vector is None:
        raise ESCOSkillEmbeddingValidationError("Embedding vector is missing.")
    if hasattr(vector, "tolist"):
        vector = vector.tolist()

    try:
        values = [float(item) for item in vector]
    except TypeError as exc:
        raise ESCOSkillEmbeddingValidationError(
            "Embedding vector must be an iterable of numeric values."
        ) from exc
    except ValueError as exc:
        raise ESCOSkillEmbeddingValidationError(
            "Embedding vector contains a non-numeric value."
        ) from exc

    if not values:
        raise ESCOSkillEmbeddingValidationError("Embedding vector is empty.")
    return values


def vector_dimension_matches(vector, expected_dimensions: int | None = None) -> bool:
    try:
        values = _coerce_vector_values(vector)
        expected = get_expected_embedding_dimensions(expected_dimensions)
    except ESCOSkillEmbeddingValidationError:
        return False
    return len(values) == expected


def validate_embedding_shape(vector, expected_dimensions: int | None = None) -> list[float]:
    values = _coerce_vector_values(vector)
    expected = get_expected_embedding_dimensions(expected_dimensions)
    if len(values) != expected:
        raise ESCOSkillEmbeddingValidationError(
            f"Embedding dimension mismatch: expected {expected}, got {len(values)}."
        )
    for value in values:
        if not math.isfinite(value):
            raise ESCOSkillEmbeddingValidationError(
                "Embedding vector contains NaN or infinite values."
            )
    return values


def embedding_model_matches(
    value,
    model_name: str,
    *,
    model_version: str | None = None,
    expected_dimensions: int | None = None,
) -> bool:
    resolved_model = resolve_embedding_model_name(model_name)
    resolved_version = resolve_embedding_version(model_version)
    expected = get_expected_embedding_dimensions(expected_dimensions)

    stored_model = str(getattr(value, "embedding_model", "") or "").strip()
    stored_version = str(getattr(value, "embedding_version", "") or "").strip()
    stored_dimensions = getattr(value, "embedding_dimensions", None)
    try:
        stored_dimensions = int(stored_dimensions)
    except (TypeError, ValueError):
        return False

    return (
        stored_model == resolved_model
        and stored_version == resolved_version
        and stored_dimensions == expected
    )


def embedding_metadata_is_complete(value) -> bool:
    stored_model = str(getattr(value, "embedding_model", "") or "").strip()
    stored_version = str(getattr(value, "embedding_version", "") or "").strip()
    stored_dimensions = getattr(value, "embedding_dimensions", None)
    updated_at = getattr(value, "embedding_updated_at", None)
    if not stored_model or not stored_version or updated_at is None:
        return False
    try:
        return int(stored_dimensions) > 0
    except (TypeError, ValueError):
        return False


def embedding_is_usable(
    value,
    *,
    model_name: str | None = None,
    model_version: str | None = None,
    expected_dimensions: int | None = None,
) -> bool:
    try:
        validated = validate_embedding_shape(
            getattr(value, "embedding", None),
            expected_dimensions=expected_dimensions,
        )
    except ESCOSkillEmbeddingValidationError:
        return False

    if model_name is None and model_version is None and expected_dimensions is None:
        return bool(validated) and embedding_metadata_is_complete(value)

    try:
        return bool(validated) and embedding_model_matches(
            value,
            model_name or getattr(value, "embedding_model", ""),
            model_version=model_version or getattr(value, "embedding_version", ""),
            expected_dimensions=expected_dimensions
            if expected_dimensions is not None
            else getattr(value, "embedding_dimensions", None),
        )
    except ESCOSkillEmbeddingValidationError:
        return False
