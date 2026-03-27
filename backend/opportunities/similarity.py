import hashlib
import logging
import math
import re
import unicodedata
from datetime import date, timedelta

from .models import Opportunite, StatutOpportunite


logger = logging.getLogger(__name__)

MAX_TOP_K = 50
MAX_CANDIDATES = 1000
RECENT_DAYS_WINDOW = 90
MIN_SIMILARITY = 0.52


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


def _build_rank_score(base_similarity, publication_date):
    # Keep similarity_score semantic, then add a small bounded recency lift
    # only for already relevant candidates to avoid score inflation.
    if base_similarity <= 0.0:
        return base_similarity
    bonus = _recency_bonus(publication_date)
    return base_similarity + bonus * (1.0 - base_similarity)


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
        "type_opportunite",
        "date_publication",
    )[:MAX_CANDIDATES]:
        processed_candidates += 1
        candidate_fingerprint = _build_content_fingerprint(candidate.titre, candidate.description)
        if source_fingerprint and candidate_fingerprint and candidate_fingerprint == source_fingerprint:
            continue

        base_similarity = cosine_similarity(source_vector, candidate.embedding_vector, assume_normalized=True)
        if base_similarity is None:
            continue
        if base_similarity < MIN_SIMILARITY:
            continue

        candidate.similarity_score = _clamp_similarity(base_similarity)
        candidate._rank_score = _clamp_similarity(  # noqa: SLF001
            _build_rank_score(base_similarity, candidate.date_publication)
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
    top_results = []
    for row in scored_rows:
        fingerprint = getattr(row, "_similarity_fingerprint", "")
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        if fingerprint:
            seen_fingerprints.add(fingerprint)
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
