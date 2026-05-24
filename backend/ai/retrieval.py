import logging
import math

from django.conf import settings
from django.db import connection, transaction

try:
    from pgvector.django import CosineDistance
except Exception:  # pragma: no cover - pgvector can be unavailable in some runtimes
    CosineDistance = None

from .embeddings import get_expected_profile_embedding_dimensions, validate_profile_embedding_vector


logger = logging.getLogger(__name__)

MAX_SEMANTIC_CANDIDATES = 300
PGVECTOR_FETCH_MULTIPLIER = 2
DEFAULT_IVFFLAT_PROBES = 2
DEFAULT_IVFFLAT_MAX_PROBES = 20

RECOMMENDATION_CANDIDATE_FIELDS = (
    "id",
    "titre",
    "description",
    "organisation_nom",
    "ville",
    "type_opportunite",
    "date_publication",
    "embedding_vector",
    "jobbert_embedding_vector",
    "jobbert_embedding_model",
    "skills",
    "normalized_skills",
    "normalized_industries",
    "extra_data",
    "normalized_contract_types",
    "normalized_work_mode",
    "contract_type",
    "availability",
    "salary",
    "experience_min",
    "experience_max",
    "experience_years",
)


def _bounded_candidate_limit(limit):
    try:
        value = int(limit or MAX_SEMANTIC_CANDIDATES)
    except (TypeError, ValueError):
        value = MAX_SEMANTIC_CANDIDATES
    return max(1, min(value, MAX_SEMANTIC_CANDIDATES))


def _vector_is_compatible(vector):
    try:
        validate_profile_embedding_vector(
            vector,
            expected_dimensions=get_expected_profile_embedding_dimensions(),
        )
    except ValueError:
        return False
    return True


def _recent_candidates(queryset, limit):
    limit = _bounded_candidate_limit(limit)
    return list(
        queryset
        .select_related(None)
        .only(*RECOMMENDATION_CANDIDATE_FIELDS)
        .order_by("-date_publication", "-id")[:limit]
    )


def _pgvector_setting_int(name, default):
    try:
        value = int(getattr(settings, name, default) or default)
    except (TypeError, ValueError):
        value = default
    return max(1, value)


def _configure_pgvector_session():
    probes = _pgvector_setting_int("RECOMMENDATION_IVFFLAT_PROBES", DEFAULT_IVFFLAT_PROBES)
    max_probes = max(
        probes,
        _pgvector_setting_int("RECOMMENDATION_IVFFLAT_MAX_PROBES", DEFAULT_IVFFLAT_MAX_PROBES),
    )
    with connection.cursor() as cursor:
        try:
            cursor.execute("SET LOCAL ivfflat.iterative_scan = relaxed_order")
            cursor.execute("SET LOCAL ivfflat.probes = %s", [probes])
            cursor.execute("SET LOCAL ivfflat.max_probes = %s", [max_probes])
        except Exception:
            logger.warning(
                "Could not configure pgvector ivfflat session settings; continuing with database defaults",
                exc_info=True,
            )


def retrieve_pgvector_candidates(user_embedding, queryset, limit, *, embedding_model=""):
    if CosineDistance is None:
        raise RuntimeError("pgvector is not available")

    source_vector = validate_profile_embedding_vector(
        user_embedding,
        expected_dimensions=get_expected_profile_embedding_dimensions(),
    )
    limit = _bounded_candidate_limit(limit)
    fetch_limit = min(MAX_SEMANTIC_CANDIDATES, limit * PGVECTOR_FETCH_MULTIPLIER)

    candidates = (
        queryset
        .select_related(None)
        .exclude(embedding_vector__isnull=True)
        .exclude(embedding_vector_pg__isnull=True)
    )
    if embedding_model:
        candidates = candidates.filter(embedding_model=embedding_model)

    results = []
    with transaction.atomic():
        _configure_pgvector_session()
        rows = candidates.annotate(
            pg_distance=CosineDistance("embedding_vector_pg", source_vector)
        ).order_by(
            "pg_distance",
            "-date_publication",
            "-id",
        ).only(
            *RECOMMENDATION_CANDIDATE_FIELDS
        )[:fetch_limit]

        for candidate in rows:
            distance = getattr(candidate, "pg_distance", None)
            if distance is None or not math.isfinite(float(distance)):
                continue
            if not _vector_is_compatible(getattr(candidate, "embedding_vector", None)):
                continue
            results.append(candidate)
            if len(results) >= limit:
                break

    logger.info(
        "profile recommendation pgvector retrieval completed requested=%s fetched=%s returned=%s",
        limit,
        fetch_limit,
        len(results),
    )
    return results


def retrieve_recommendation_candidates(user_embedding, queryset, limit, *, embedding_model=""):
    if not user_embedding:
        return _recent_candidates(queryset, limit)

    if not getattr(settings, "OPPORTUNITY_PGVECTOR_ENABLED", True):
        logger.info("profile recommendation pgvector retrieval disabled; using bounded recent fallback")
        return _recent_candidates(queryset, limit)

    try:
        return retrieve_pgvector_candidates(
            user_embedding,
            queryset,
            limit,
            embedding_model=embedding_model,
        )
    except Exception:
        logger.exception("profile recommendation pgvector retrieval failed; using bounded recent fallback")
        return _recent_candidates(queryset, limit)
