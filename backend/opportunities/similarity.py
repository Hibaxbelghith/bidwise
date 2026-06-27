import hashlib
import logging
import math
import re
import unicodedata
from datetime import date, timedelta
from functools import lru_cache

from django.conf import settings

from ai.business_families import families_are_compatible, normalize_family_set

try:
    from pgvector.django import CosineDistance
except Exception:  # pragma: no cover - optional dependency at runtime
    CosineDistance = None

from .models import Opportunite, SourceOpportunite, StatutOpportunite, TypeOpportunite


logger = logging.getLogger(__name__)

MAX_TOP_K = 50
MAX_CANDIDATES = 1000
RECENT_DAYS_WINDOW = 90
MIN_SIMILARITY = 0.60
MAX_SIMILAR_PER_SOURCE_RATIO = 0.6
MIN_SIMILAR_PER_SOURCE = 2
STAGE_KEEJOB_BIAS = 0.03
BROAD_SIMILARITY_FAMILIES = {
    "administration",
    "hr_administration",
    "customer_support",
    "other",
}
MIN_STRUCTURED_TERM_OVERLAP = 2


def _to_float_vector(vector):
    if not isinstance(vector, list) or not vector:
        return []
    values = []
    for item in vector:
        try:
            value = float(item)
        except (TypeError, ValueError):
            return []
        if not math.isfinite(value):
            return []
        values.append(value)
    return values


def _clamp_similarity(score):
    return max(-1.0, min(1.0, float(score)))


def cosine_similarity(vector_a, vector_b, assume_normalized=True):
    left = _to_float_vector(vector_a)
    right = _to_float_vector(vector_b)
    if not left or not right or len(left) != len(right):
        return None

    dot = float(sum(a * b for a, b in zip(left, right)))
    if assume_normalized:
        return _clamp_similarity(dot)

    norm_left = math.sqrt(sum(value * value for value in left))
    norm_right = math.sqrt(sum(value * value for value in right))
    if norm_left == 0.0 or norm_right == 0.0:
        return None
    return _clamp_similarity(dot / (norm_left * norm_right))


def _normalize_text_for_fingerprint(value):
    if not value:
        return ""
    cleaned = unicodedata.normalize("NFKD", str(value))
    cleaned = "".join(ch for ch in cleaned if not unicodedata.combining(ch))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _semantic_terms(value):
    normalized = _normalize_text_for_fingerprint(value)
    return {token for token in normalized.split() if len(token) > 2}


def _as_list(value):
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if value:
        return [str(value).strip()]
    return []


def _llm_enrichment(opportunity):
    extra_data = getattr(opportunity, "extra_data", None)
    if not isinstance(extra_data, dict):
        return {}
    enrichment = extra_data.get("llm_enrichment") or {}
    return enrichment if isinstance(enrichment, dict) else {}


def _opportunity_similarity_terms(opportunity):
    enrichment = _llm_enrichment(opportunity)
    values = [
        getattr(opportunity, "titre", ""),
        *_as_list(getattr(opportunity, "skills", [])),
        *_as_list(enrichment.get("canonical_role")),
        *_as_list(enrichment.get("target_roles")),
        *_as_list(enrichment.get("skills")),
        *_as_list(enrichment.get("tools")),
    ]
    terms = set()
    for value in values:
        terms.update(_semantic_terms(value))
    return terms - _opportunity_location_terms(opportunity)


def _opportunity_title_terms(opportunity):
    return _semantic_terms(getattr(opportunity, "titre", "")) - _opportunity_location_terms(opportunity)


def _opportunity_skill_terms(opportunity):
    enrichment = _llm_enrichment(opportunity)
    values = [
        *_as_list(getattr(opportunity, "skills", [])),
        *_as_list(enrichment.get("skills")),
        *_as_list(enrichment.get("tools")),
    ]
    terms = set()
    for value in values:
        terms.update(_semantic_terms(value))
    return terms - _opportunity_location_terms(opportunity)


def _opportunity_skill_token_sets(opportunity):
    enrichment = _llm_enrichment(opportunity)
    values = [
        *_as_list(getattr(opportunity, "skills", [])),
        *_as_list(enrichment.get("skills")),
        *_as_list(enrichment.get("tools")),
    ]
    location_terms = _opportunity_location_terms(opportunity)
    token_sets = []
    for value in values:
        terms = _semantic_terms(value) - location_terms
        if terms:
            token_sets.append(terms)
    return token_sets


def _has_structured_skill_phrase_support(anchor, candidate):
    for anchor_terms in _opportunity_skill_token_sets(anchor):
        for candidate_terms in _opportunity_skill_token_sets(candidate):
            if len(anchor_terms.intersection(candidate_terms)) >= MIN_STRUCTURED_TERM_OVERLAP:
                return True
    return False


def _opportunity_location_terms(opportunity):
    return _semantic_terms(getattr(opportunity, "ville", ""))


def _opportunity_business_families(opportunity):
    return normalize_family_set(_llm_enrichment(opportunity).get("business_families")) - {"other"}


def _specialized_families(families):
    return set(families or set()) - BROAD_SIMILARITY_FAMILIES


def _has_structured_similarity_signals(opportunity):
    enrichment = _llm_enrichment(opportunity)
    return bool(
        _as_list(getattr(opportunity, "skills", []))
        or _as_list(enrichment.get("skills"))
        or _as_list(enrichment.get("tools"))
        or _as_list(enrichment.get("domains"))
        or _as_list(enrichment.get("business_families"))
    )


def _passes_similarity_business_guard(anchor, candidate):
    if not _has_structured_similarity_signals(anchor) and not _has_structured_similarity_signals(candidate):
        return True

    anchor_terms = _opportunity_similarity_terms(anchor)
    candidate_terms = _opportunity_similarity_terms(candidate)
    anchor_skill_terms = _opportunity_skill_terms(anchor)
    candidate_skill_terms = _opportunity_skill_terms(candidate)
    skill_phrase_support = _has_structured_skill_phrase_support(anchor, candidate)
    title_title_support = len(
        _opportunity_title_terms(anchor).intersection(_opportunity_title_terms(candidate))
    ) >= MIN_STRUCTURED_TERM_OVERLAP
    candidate_title_skill_support = bool(
        _opportunity_title_terms(candidate).intersection(anchor_skill_terms)
    )
    structured_support = skill_phrase_support or candidate_title_skill_support or title_title_support

    anchor_families = _opportunity_business_families(anchor)
    candidate_families = _opportunity_business_families(candidate)
    if anchor_families and candidate_families:
        anchor_specialized = _specialized_families(anchor_families)
        candidate_specialized = _specialized_families(candidate_families)

        # If the anchor has a precise business family, do not let broad support
        # families (administration, customer support) dominate the result.
        if anchor_specialized:
            family_supported = families_are_compatible(
                anchor_specialized,
                candidate_specialized or candidate_families,
            )
            return family_supported and structured_support
        if candidate_specialized:
            family_supported = families_are_compatible(anchor_families, candidate_specialized)
            return family_supported and structured_support
        return families_are_compatible(anchor_families, candidate_families) and structured_support

    if (
        anchor_terms
        and candidate_terms
        and structured_support
    ):
        return True

    return False


def _build_content_fingerprint(title, description):
    normalized_title = _normalize_text_for_fingerprint(title)[:50]
    normalized_description = _normalize_text_for_fingerprint(description)[:200]
    payload = f"{normalized_title}|{normalized_description}".strip("|")
    if not payload:
        return ""
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _recency_bonus(publication_date):
    if not publication_date:
        return 0.0
    age_days = (date.today() - publication_date).days
    if age_days < 0:
        age_days = 0
    if age_days <= 7:
        return 0.05
    if age_days <= 30:
        return 0.03
    if age_days <= 90:
        return 0.01
    return 0.0


@lru_cache(maxsize=1)
def _keejob_source_id():
    return (
        SourceOpportunite.objects.filter(nom="Keejob")
        .values_list("id", flat=True)
        .first()
    )


def _stage_source_bias(opportunity_type, source_id):
    if opportunity_type != TypeOpportunite.STAGE or source_id is None:
        return 0.0

    keejob_id = _keejob_source_id()
    if source_id == keejob_id:
        return STAGE_KEEJOB_BIAS
    return 0.0


def _source_cap_for_row(*, limit, default_cap, opportunity_type, source_id):
    return default_cap


def _build_rank_score(base_similarity, publication_date, source_bias=0.0):
    # Keep similarity_score semantic, then add a small bounded recency lift
    # only for already relevant candidates to avoid score inflation.
    if base_similarity <= 0.0:
        return base_similarity
    bonus = _recency_bonus(publication_date)
    return base_similarity + bonus * (1.0 - base_similarity) + float(source_bias or 0.0)


def _max_per_source(limit):
    if limit <= 3:
        return limit
    return max(MIN_SIMILAR_PER_SOURCE, int(math.ceil(limit * MAX_SIMILAR_PER_SOURCE_RATIO)))


def find_similar_opportunities(opportunity, top_k=5, queryset=None, enforce_same_type=True):
    source_vector = _to_float_vector(getattr(opportunity, "embedding_vector", None))
    if not source_vector:
        return []
    source_fingerprint = _build_content_fingerprint(
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
    )

    try:
        limit = int(top_k or 5)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, MAX_TOP_K))

    candidates = queryset or Opportunite.objects.all()
    candidates = candidates.select_related(None)
    candidates = (
        candidates.exclude(pk=opportunity.pk)
        .exclude(embedding_vector__isnull=True)
        .filter(statut=StatutOpportunite.ACTIVE)
    )
    if enforce_same_type and getattr(opportunity, "type_opportunite", None):
        candidates = candidates.filter(type_opportunite=opportunity.type_opportunite)
    if getattr(opportunity, "embedding_model", ""):
        candidates = candidates.filter(embedding_model=opportunity.embedding_model)
    cutoff_date = date.today() - timedelta(days=RECENT_DAYS_WINDOW)
    candidates = candidates.filter(date_publication__gte=cutoff_date).order_by("-date_publication", "-id")

    scored_rows = []
    processed_candidates = 0
    for candidate in candidates.only(
        "id",
        "titre",
        "description",
        "embedding_vector",
        "extra_data",
        "skills",
        "source_id",
        "type_opportunite",
        "date_publication",
        "ville",
    )[:MAX_CANDIDATES]:
        processed_candidates += 1
        candidate_fingerprint = _build_content_fingerprint(candidate.titre, candidate.description)
        if source_fingerprint and candidate_fingerprint and candidate_fingerprint == source_fingerprint:
            continue
        if not _passes_similarity_business_guard(opportunity, candidate):
            continue

        base_similarity = cosine_similarity(source_vector, candidate.embedding_vector, assume_normalized=True)
        if base_similarity is None:
            continue
        if base_similarity < MIN_SIMILARITY:
            continue

        source_bias = _stage_source_bias(
            getattr(opportunity, "type_opportunite", None),
            getattr(candidate, "source_id", None),
        )

        candidate.similarity_score = _clamp_similarity(base_similarity)
        candidate._rank_score = _clamp_similarity(  # noqa: SLF001
            _build_rank_score(base_similarity, candidate.date_publication, source_bias)
        )
        candidate._similarity_fingerprint = candidate_fingerprint  # noqa: SLF001
        scored_rows.append(candidate)

    scored_rows.sort(
        key=lambda row: (
            row._rank_score,  # noqa: SLF001
            row.similarity_score,
            row.date_publication.toordinal() if row.date_publication else 0,
            row.id,
        ),
        reverse=True,
    )

    seen_fingerprints = set()
    source_counts = {}
    top_results = []
    per_source_cap = _max_per_source(limit)
    anchor_type = getattr(opportunity, "type_opportunite", None)
    for row in scored_rows:
        source_id = getattr(row, "source_id", None)
        row_source_cap = _source_cap_for_row(
            limit=limit,
            default_cap=per_source_cap,
            opportunity_type=anchor_type,
            source_id=source_id,
        )
        if source_id is not None and source_counts.get(source_id, 0) >= row_source_cap:
            continue

        fingerprint = getattr(row, "_similarity_fingerprint", "")
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        if fingerprint:
            seen_fingerprints.add(fingerprint)

        if source_id is not None:
            source_counts[source_id] = source_counts.get(source_id, 0) + 1

        top_results.append(row)
        if len(top_results) >= limit:
            break

    logger.info(
        "similarity computed for id=%s, candidates=%s, returned=%s",
        getattr(opportunity, "pk", None),
        processed_candidates,
        len(top_results),
    )
    return top_results


def find_similar_opportunities_pgvector(opportunity, top_k=5, queryset=None, enforce_same_type=True):
    if CosineDistance is None:
        raise RuntimeError("pgvector is not available")

    source_vector = _to_float_vector(getattr(opportunity, "embedding_vector", None))
    if not source_vector:
        return []
    source_fingerprint = _build_content_fingerprint(
        getattr(opportunity, "titre", ""),
        getattr(opportunity, "description", ""),
    )

    try:
        limit = int(top_k or 5)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, MAX_TOP_K))

    candidates = queryset or Opportunite.objects.all()
    candidates = candidates.select_related(None)
    candidates = (
        candidates.exclude(pk=opportunity.pk)
        .exclude(embedding_vector_pg__isnull=True)
        .filter(statut=StatutOpportunite.ACTIVE)
    )
    if enforce_same_type and getattr(opportunity, "type_opportunite", None):
        candidates = candidates.filter(type_opportunite=opportunity.type_opportunite)
    if getattr(opportunity, "embedding_model", ""):
        candidates = candidates.filter(embedding_model=opportunity.embedding_model)

    cutoff_date = date.today() - timedelta(days=RECENT_DAYS_WINDOW)
    candidates = candidates.filter(date_publication__gte=cutoff_date)

    # cosine distance in pgvector: distance = 1 - cosine_similarity
    max_distance = 1.0 - MIN_SIMILARITY
    candidates = candidates.annotate(
        pg_distance=CosineDistance("embedding_vector_pg", source_vector)
    ).filter(
        pg_distance__lte=max_distance
    ).order_by(
        "pg_distance", "-date_publication", "-id"
    )

    scored_rows = []
    processed_candidates = 0
    for candidate in candidates.only(
        "id",
        "titre",
        "description",
        "extra_data",
        "skills",
        "source_id",
        "type_opportunite",
        "date_publication",
        "ville",
    )[:MAX_CANDIDATES]:
        processed_candidates += 1
        candidate_fingerprint = _build_content_fingerprint(candidate.titre, candidate.description)
        if source_fingerprint and candidate_fingerprint and candidate_fingerprint == source_fingerprint:
            continue
        if not _passes_similarity_business_guard(opportunity, candidate):
            continue

        distance = getattr(candidate, "pg_distance", None)
        if distance is None:
            continue

        base_similarity = _clamp_similarity(1.0 - float(distance))
        if base_similarity < MIN_SIMILARITY:
            continue

        source_bias = _stage_source_bias(
            getattr(opportunity, "type_opportunite", None),
            getattr(candidate, "source_id", None),
        )

        candidate.similarity_score = base_similarity
        candidate._rank_score = _clamp_similarity(  # noqa: SLF001
            _build_rank_score(base_similarity, candidate.date_publication, source_bias)
        )
        candidate._similarity_fingerprint = candidate_fingerprint  # noqa: SLF001
        scored_rows.append(candidate)

    scored_rows.sort(
        key=lambda row: (
            row._rank_score,  # noqa: SLF001
            row.similarity_score,
            row.date_publication.toordinal() if row.date_publication else 0,
            row.id,
        ),
        reverse=True,
    )

    seen_fingerprints = set()
    source_counts = {}
    top_results = []
    per_source_cap = _max_per_source(limit)
    anchor_type = getattr(opportunity, "type_opportunite", None)
    for row in scored_rows:
        source_id = getattr(row, "source_id", None)
        row_source_cap = _source_cap_for_row(
            limit=limit,
            default_cap=per_source_cap,
            opportunity_type=anchor_type,
            source_id=source_id,
        )
        if source_id is not None and source_counts.get(source_id, 0) >= row_source_cap:
            continue

        fingerprint = getattr(row, "_similarity_fingerprint", "")
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        if fingerprint:
            seen_fingerprints.add(fingerprint)

        if source_id is not None:
            source_counts[source_id] = source_counts.get(source_id, 0) + 1

        top_results.append(row)
        if len(top_results) >= limit:
            break

    logger.info(
        "similarity computed (pgvector) for id=%s, candidates=%s, returned=%s",
        getattr(opportunity, "pk", None),
        processed_candidates,
        len(top_results),
    )
    return top_results


def find_similar_opportunities_with_fallback(opportunity, top_k=5, queryset=None, enforce_same_type=True):
    if not getattr(settings, "OPPORTUNITY_PGVECTOR_ENABLED", False):
        return find_similar_opportunities(
            opportunity=opportunity,
            top_k=top_k,
            queryset=queryset,
            enforce_same_type=enforce_same_type,
        )

    if CosineDistance is None:
        logger.warning(
            "OPPORTUNITY_PGVECTOR_ENABLED is true but pgvector is unavailable; using Python fallback"
        )
        return find_similar_opportunities(
            opportunity=opportunity,
            top_k=top_k,
            queryset=queryset,
            enforce_same_type=enforce_same_type,
        )

    try:
        pgvector_results = find_similar_opportunities_pgvector(
            opportunity=opportunity,
            top_k=top_k,
            queryset=queryset,
            enforce_same_type=enforce_same_type,
        )
        if pgvector_results:
            return pgvector_results

        # Graceful fallback while the pgvector backfill is still in progress.
        # If candidates exist with Python embeddings, avoid returning an empty
        # recommendation set only because embedding_vector_pg is not populated yet.
        fallback_candidates = (queryset or Opportunite.objects.all()).exclude(
            pk=getattr(opportunity, "pk", None)
        ).exclude(
            embedding_vector__isnull=True
        ).filter(
            statut=StatutOpportunite.ACTIVE
        )
        if enforce_same_type and getattr(opportunity, "type_opportunite", None):
            fallback_candidates = fallback_candidates.filter(type_opportunite=opportunity.type_opportunite)
        if getattr(opportunity, "embedding_model", ""):
            fallback_candidates = fallback_candidates.filter(embedding_model=opportunity.embedding_model)
        cutoff_date = date.today() - timedelta(days=RECENT_DAYS_WINDOW)
        fallback_candidates = fallback_candidates.filter(date_publication__gte=cutoff_date)

        if fallback_candidates.exists():
            logger.info(
                "pgvector returned no candidates for id=%s; using Python fallback while pg field coverage is incomplete",
                getattr(opportunity, "pk", None),
            )
            return find_similar_opportunities(
                opportunity=opportunity,
                top_k=top_k,
                queryset=queryset,
                enforce_same_type=enforce_same_type,
            )

        return pgvector_results
    except Exception:
        logger.exception(
            "pgvector similarity failed for id=%s; using Python fallback",
            getattr(opportunity, "pk", None),
        )
        return find_similar_opportunities(
            opportunity=opportunity,
            top_k=top_k,
            queryset=queryset,
            enforce_same_type=enforce_same_type,
        )
