from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import math
from typing import Any

from django.conf import settings
from django.core.cache import cache

from opportunities.extraction.profile_terms import (
    INTEREST_ALIAS_MAP,
    ROLE_ALIAS_MAP,
    SKILL_ALIAS_MAP,
    canonicalize_industry,
    canonicalize_known_role,
    canonicalize_known_skill,
    is_known_industry,
    is_known_role,
    is_known_skill,
    is_rejected_profile_term,
)
from opportunities.normalization.industries import normalize_industries
from opportunities.models import ProfileSuggestion, ProfileSuggestionType
from opportunities.normalization.text import clean_display_text, normalize_lookup_key


DEFAULT_LIMIT = 10
MAX_LIMIT = 25
MAX_QUERY_LENGTH = int(getattr(settings, "PROFILE_AUTOCOMPLETE_MAX_QUERY_LENGTH", 80))
MAX_CACHED_SUGGESTIONS = int(getattr(settings, "PROFILE_AUTOCOMPLETE_CACHE_LIMIT", 1500))
CACHE_TIMEOUT_SECONDS = int(getattr(settings, "PROFILE_AUTOCOMPLETE_CACHE_TIMEOUT_SECONDS", 300))

MIN_ROLE_FREQUENCY = int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_ROLE_FREQUENCY", 2))
MIN_SKILL_FREQUENCY = int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_SKILL_FREQUENCY", 2))
MIN_INTEREST_FREQUENCY = int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_INTEREST_FREQUENCY", 1))
MIN_CONFIDENCE = float(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_CONFIDENCE", 0.55))
FUZZY_THRESHOLD = float(getattr(settings, "PROFILE_AUTOCOMPLETE_FUZZY_THRESHOLD", 0.78))
ROLE_FUZZY_THRESHOLD = float(getattr(settings, "PROFILE_AUTOCOMPLETE_ROLE_FUZZY_THRESHOLD", 0.88))
MIN_FUZZY_QUERY_LENGTH = int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_FUZZY_QUERY_LENGTH", 4))

MATCH_RANK = {
    "exact": 0,
    "canonical_prefix": 1,
    "alias_prefix": 2,
    "contains": 3,
    "fuzzy": 4,
    "popular": 5,
}
MATCH_BASE_SCORE = {
    "exact": 1.0,
    "canonical_prefix": 0.93,
    "alias_prefix": 0.88,
    "contains": 0.72,
    "fuzzy": 0.58,
    "popular": 0.38,
}


@dataclass(frozen=True)
class MatchResult:
    score: float
    match_type: str
    token_overlap: float = 0.0
    exactness: float = 0.0


def _term_type_value(value: str) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _min_frequency(term_type: str) -> int:
    if term_type == ProfileSuggestionType.ROLE.value:
        return MIN_ROLE_FREQUENCY
    if term_type == ProfileSuggestionType.INTEREST.value:
        return MIN_INTEREST_FREQUENCY
    return MIN_SKILL_FREQUENCY


def coerce_limit(value: Any, *, default: int = DEFAULT_LIMIT) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(limit, MAX_LIMIT))


def sanitize_query_input(value: Any) -> str:
    return clean_display_text(value, max_length=MAX_QUERY_LENGTH)


def _cache_key(term_type: str) -> str:
    return f"profile_suggestions:v3:{term_type}"


def _safe_cache_get(key: str) -> Any:
    try:
        return cache.get(key)
    except Exception:
        return None


def _safe_cache_set(key: str, value: Any) -> None:
    try:
        cache.set(key, value, CACHE_TIMEOUT_SECONDS)
    except Exception:
        pass


def _is_serving_safe_row(term_type: str, row: dict[str, Any]) -> bool:
    canonical = row.get("canonical", "")
    if _cross_type_known(term_type, canonical):
        return False
    if is_rejected_profile_term(term_type, canonical):
        return False
    return True


def _active_suggestion_rows(term_type: str) -> list[dict[str, Any]]:
    cached = _safe_cache_get(_cache_key(term_type))
    if cached is not None:
        return cached

    rows = list(
        ProfileSuggestion.objects.filter(
            term_type=term_type,
            is_active=True,
            frequency__gte=_min_frequency(term_type),
            confidence__gte=MIN_CONFIDENCE,
        )
        .values(
            "id",
            "term_type",
            "canonical",
            "normalized_key",
            "aliases",
            "frequency",
            "confidence",
            "metadata",
        )
        .order_by("-frequency", "-confidence", "canonical")[:MAX_CACHED_SUGGESTIONS]
    )
    rows = [row for row in rows if _is_serving_safe_row(term_type, row)]
    _safe_cache_set(_cache_key(term_type), rows)
    return rows


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _dictionary_alias_keys(term_type: str, canonical: Any) -> list[str]:
    canonical_key = normalize_lookup_key(canonical)
    if not canonical_key:
        return []

    alias_map = _dictionary_alias_map(term_type)
    return [
        alias_key
        for alias_key, alias_canonical in alias_map.items()
        if normalize_lookup_key(alias_canonical) == canonical_key
    ]


def _alias_keys(row: dict[str, Any]) -> list[str]:
    metadata = _metadata(row)
    metadata_alias_keys = metadata.get("alias_keys")
    if isinstance(metadata_alias_keys, list) and metadata_alias_keys:
        keys = [str(key) for key in metadata_alias_keys]
    else:
        aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
        keys = [normalize_lookup_key(row.get("canonical", ""))]
        keys.extend(normalize_lookup_key(alias) for alias in aliases)
    keys.extend(_dictionary_alias_keys(row.get("term_type"), row.get("canonical", "")))
    return [key for key in dict.fromkeys(keys) if key]


def _token_keys(row: dict[str, Any]) -> list[str]:
    metadata_token_keys = _metadata(row).get("token_keys")
    keys = [str(key) for key in metadata_token_keys] if isinstance(metadata_token_keys, list) else []
    for alias_key in [_canonical_key(row), *_alias_keys(row)]:
        keys.extend(alias_key.split())
    return [key for key in dict.fromkeys(keys) if key]


def _compact_keys(row: dict[str, Any]) -> list[str]:
    metadata = _metadata(row)
    metadata_compact_keys = metadata.get("compact_keys") or metadata.get("compact_alias_keys")
    keys = [str(key) for key in metadata_compact_keys] if isinstance(metadata_compact_keys, list) else []
    for alias_key in [_canonical_key(row), *_alias_keys(row)]:
        compact_key = alias_key.replace(" ", "")
        if compact_key:
            keys.append(compact_key)
    return [key for key in dict.fromkeys(keys) if key]


def _canonical_key(row: dict[str, Any]) -> str:
    metadata_key = _metadata(row).get("canonical_key")
    if isinstance(metadata_key, str) and metadata_key:
        return metadata_key
    return normalize_lookup_key(row.get("canonical", ""))


def _token_overlap(query_key: str, candidate_key: str) -> float:
    query_tokens = set(query_key.split())
    candidate_tokens = set(candidate_key.split())
    if not query_tokens or not candidate_tokens:
        return 0.0
    return len(query_tokens & candidate_tokens) / len(query_tokens)


def _compact_key(value: str) -> str:
    return normalize_lookup_key(value).replace(" ", "")


def _compact_match_allowed(query_key: str) -> bool:
    return len(query_key.replace(" ", "")) >= MIN_FUZZY_QUERY_LENGTH


def _token_prefix_match(query_key: str, candidate_key: str) -> bool:
    if not query_key:
        return False
    query_tokens = query_key.split()
    candidate_tokens = candidate_key.split()
    if len(query_tokens) == 1:
        token = query_tokens[0]
        return any(candidate.startswith(token) for candidate in candidate_tokens)
    return candidate_key.startswith(query_key)


def _prefix_match(query_key: str, candidate_key: str) -> bool:
    if candidate_key.startswith(query_key) or _token_prefix_match(query_key, candidate_key):
        return True
    if not _compact_match_allowed(query_key):
        return False
    query_compact = _compact_key(query_key)
    candidate_compact = _compact_key(candidate_key)
    return bool(query_compact and candidate_compact.startswith(query_compact))


def _variant_prefix_match(query_key: str, variants: list[str]) -> bool:
    if not query_key:
        return False
    if query_key in variants:
        return True
    return any(variant.startswith(query_key) for variant in variants)


def _contains_match(query_key: str, candidate_key: str) -> bool:
    if query_key in candidate_key:
        return True
    if not _compact_match_allowed(query_key):
        return False
    query_compact = _compact_key(query_key)
    candidate_compact = _compact_key(candidate_key)
    return bool(query_compact and query_compact in candidate_compact)


def _best_fuzzy_ratio(query_key: str, candidate_key: str) -> float:
    ratios = [SequenceMatcher(None, query_key, candidate_key).ratio()]
    for query_token in query_key.split():
        if len(query_token) < MIN_FUZZY_QUERY_LENGTH:
            continue
        ratios.extend(
            SequenceMatcher(None, query_token, candidate_token).ratio()
            for candidate_token in candidate_key.split()
        )
    return max(ratios) if ratios else 0.0


def _fuzzy_allowed(query_key: str, candidate_key: str, ratio: float, *, term_type: str) -> bool:
    if len(query_key.replace(" ", "")) < MIN_FUZZY_QUERY_LENGTH:
        return False
    threshold = ROLE_FUZZY_THRESHOLD if term_type == ProfileSuggestionType.ROLE.value else FUZZY_THRESHOLD
    if ratio < threshold:
        return False
    if not query_key or not candidate_key:
        return False
    query_first = query_key[0]
    candidate_tokens = candidate_key.split()
    if any(token.startswith(query_first) for token in candidate_tokens):
        return True
    return _token_overlap(query_key, candidate_key) > 0.0


def _match_score(query_key: str, row: dict[str, Any]) -> MatchResult:
    term_type = row.get("term_type")
    canonical_key = _canonical_key(row)
    alias_keys = _alias_keys(row)
    token_keys = _token_keys(row)
    compact_keys = _compact_keys(row)
    query_compact = query_key.replace(" ", "")

    if not query_key:
        return MatchResult(score=0.0, match_type="popular")

    if canonical_key == query_key:
        return MatchResult(score=1.0, match_type="exact", token_overlap=1.0, exactness=1.0)
    if query_key in alias_keys or query_key in token_keys:
        return MatchResult(score=0.98, match_type="exact", token_overlap=1.0, exactness=0.96)

    if _prefix_match(query_key, canonical_key):
        return MatchResult(
            score=0.93,
            match_type="canonical_prefix",
            token_overlap=_token_overlap(query_key, canonical_key),
            exactness=len(query_key) / max(len(canonical_key), 1),
        )

    best_alias_prefix = ""
    if _variant_prefix_match(query_key, token_keys):
        best_alias_prefix = query_key
    if _compact_match_allowed(query_key) and _variant_prefix_match(query_compact, compact_keys):
        best_alias_prefix = best_alias_prefix or query_key
    for alias_key in alias_keys:
        if alias_key == canonical_key:
            continue
        if _prefix_match(query_key, alias_key):
            if not best_alias_prefix or len(alias_key) < len(best_alias_prefix):
                best_alias_prefix = alias_key
    if best_alias_prefix:
        return MatchResult(
            score=0.88,
            match_type="alias_prefix",
            token_overlap=_token_overlap(query_key, best_alias_prefix),
            exactness=len(query_key) / max(len(best_alias_prefix), 1),
        )

    best_contains = ""
    for alias_key in [canonical_key, *alias_keys]:
        if _contains_match(query_key, alias_key):
            if not best_contains or len(alias_key) < len(best_contains):
                best_contains = alias_key
    if best_contains:
        return MatchResult(
            score=0.72,
            match_type="contains",
            token_overlap=_token_overlap(query_key, best_contains),
            exactness=len(query_key) / max(len(best_contains), 1),
        )

    best_fuzzy = 0.0
    best_fuzzy_key = canonical_key
    for alias_key in [canonical_key, *alias_keys]:
        ratio = _best_fuzzy_ratio(query_key, alias_key)
        if ratio > best_fuzzy:
            best_fuzzy = ratio
            best_fuzzy_key = alias_key
    if _fuzzy_allowed(query_key, best_fuzzy_key, best_fuzzy, term_type=term_type):
        return MatchResult(
            score=best_fuzzy,
            match_type="fuzzy",
            token_overlap=_token_overlap(query_key, best_fuzzy_key),
            exactness=best_fuzzy,
        )

    return MatchResult(score=0.0, match_type="none")


def _quality(row: dict[str, Any]) -> float:
    value = _metadata(row).get("quality", 0.0)
    try:
        return max(0.0, min(float(value), 1.0))
    except (TypeError, ValueError):
        return 0.0


def _final_score(match: MatchResult, row: dict[str, Any]) -> float:
    frequency = int(row.get("frequency") or 0)
    confidence = max(0.0, min(float(row.get("confidence") or 0.0), 1.0))
    popularity = min(math.log1p(frequency) / math.log1p(100), 1.0)
    base = MATCH_BASE_SCORE.get(match.match_type, 0.0)

    if match.match_type == "popular":
        return popularity * 0.58 + confidence * 0.27 + _quality(row) * 0.15

    return (
        base * 0.72
        + popularity * 0.1
        + confidence * 0.08
        + _quality(row) * 0.05
        + match.token_overlap * 0.03
        + match.exactness * 0.02
    )


def _serialize_suggestion(
    row: dict[str, Any],
    *,
    score: float,
    match_type: str,
) -> dict[str, Any]:
    aliases = row.get("aliases") if isinstance(row.get("aliases"), list) else []
    return {
        "id": row["id"],
        "type": row["term_type"].lower(),
        "value": row["canonical"],
        "label": row["canonical"],
        "aliases": aliases[:8],
        "frequency": row["frequency"],
        "confidence": round(float(row.get("confidence") or 0.0), 4),
        "score": round(max(0.0, min(score, 1.0)), 4),
        "match": match_type,
    }


def _dictionary_alias_map(term_type: str) -> dict[str, str]:
    if term_type == ProfileSuggestionType.SKILL.value:
        return SKILL_ALIAS_MAP
    if term_type == ProfileSuggestionType.ROLE.value:
        return ROLE_ALIAS_MAP
    if term_type == ProfileSuggestionType.INTEREST.value:
        return INTEREST_ALIAS_MAP
    return {}


def _dictionary_row_for_canonical(term_type: str, canonical: str) -> dict[str, Any] | None:
    if _cross_type_known(term_type, canonical):
        return None
    if is_rejected_profile_term(term_type, canonical):
        return None

    aliases = [
        key
        for key, alias_canonical in _dictionary_alias_map(term_type).items()
        if normalize_lookup_key(alias_canonical) == normalize_lookup_key(canonical)
    ]
    return {
        "id": 0,
        "term_type": term_type,
        "canonical": canonical,
        "normalized_key": normalize_lookup_key(canonical),
        "aliases": aliases[:8],
        "frequency": 0,
        "confidence": 1.0,
        "metadata": {
            "canonical_key": normalize_lookup_key(canonical),
            "alias_keys": aliases,
            "quality": 1.0,
        },
    }


def _dictionary_row(term_type: str, query_key: str) -> dict[str, Any] | None:
    canonical = _dictionary_canonical(term_type, query_key)
    if not canonical:
        return None
    return _dictionary_row_for_canonical(term_type, canonical)


def _dictionary_candidate_rows(term_type: str) -> list[dict[str, Any]]:
    if term_type != ProfileSuggestionType.INTEREST.value:
        return []
    canonicals = sorted(set(_dictionary_alias_map(term_type).values()))
    return [
        row
        for canonical in canonicals
        if (row := _dictionary_row_for_canonical(term_type, canonical)) is not None
    ]


def suggest_profile_terms(
    term_type: str,
    query: str = "",
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    term_type = _term_type_value(term_type)
    if term_type not in ProfileSuggestionType.values:
        raise ValueError(f"Unsupported suggestion type: {term_type}")

    sanitized_query = sanitize_query_input(query)
    query_key = normalize_lookup_key(sanitized_query)
    limit = coerce_limit(limit)

    ranked = []
    seen_candidate_keys: set[str] = set()
    serving_rows = _active_suggestion_rows(term_type)
    if term_type == ProfileSuggestionType.INTEREST.value:
        serving_rows = [*serving_rows, *_dictionary_candidate_rows(term_type)]

    for row in serving_rows:
        row_key = normalize_lookup_key(row.get("canonical", ""))
        if row_key in seen_candidate_keys:
            continue
        seen_candidate_keys.add(row_key)
        match = _match_score(query_key, row)
        if match.match_type == "none":
            continue
        score = _final_score(match, row)
        fuzzy_threshold = (
            ROLE_FUZZY_THRESHOLD
            if term_type == ProfileSuggestionType.ROLE.value
            else FUZZY_THRESHOLD
        )
        if query_key and match.match_type == "fuzzy" and match.score < fuzzy_threshold:
            continue
        ranked.append(
            (
                MATCH_RANK.get(match.match_type, 99),
                -score,
                -int(row.get("frequency") or 0),
                row.get("canonical") or "",
                match.match_type,
                score,
                int(row.get("id") or 0),
                row,
            )
        )

    if query_key:
        dictionary_row = _dictionary_row(term_type, query_key)
        existing_keys = {
            normalize_lookup_key(row.get("canonical", ""))
            for *_rank_fields, row in ranked
        }
        dictionary_key = (
            normalize_lookup_key(dictionary_row.get("canonical", ""))
            if dictionary_row
            else ""
        )
        if dictionary_row and dictionary_key not in existing_keys:
            ranked.append(
                (
                    MATCH_RANK["exact"],
                    -0.97,
                    0,
                    dictionary_row["canonical"],
                    "exact",
                    0.97,
                    0,
                    dictionary_row,
                )
            )

    ranked.sort()
    results = [
        _serialize_suggestion(row, score=score, match_type=match_type)
        for _rank, _neg_score, _neg_frequency, _canonical, match_type, score, _id, row in ranked[:limit]
    ]
    return {
        "query": sanitized_query,
        "type": term_type.lower(),
        "count": len(results),
        "results": results,
    }


def _dictionary_canonical(term_type: str, value: Any) -> str | None:
    if term_type == ProfileSuggestionType.SKILL.value:
        return canonicalize_known_skill(value)
    if term_type == ProfileSuggestionType.ROLE.value:
        return canonicalize_known_role(value)
    if term_type == ProfileSuggestionType.INTEREST.value:
        return canonicalize_industry(value) or (normalize_industries(value) or [None])[0]
    return None


def _cross_type_known(term_type: str, value: Any) -> bool:
    if term_type == ProfileSuggestionType.SKILL.value:
        return is_known_role(value) or is_known_industry(value)
    if term_type == ProfileSuggestionType.ROLE.value:
        return is_known_skill(value) or is_known_industry(value)
    if term_type == ProfileSuggestionType.INTEREST.value:
        return is_known_skill(value) or is_known_role(value)
    return False


def normalize_profile_terms(
    term_type: str,
    values: list[str],
    *,
    preserve_unknown: bool = True,
    preserve_unknown_roles: bool = False,
) -> list[str]:
    term_type = _term_type_value(term_type)
    if term_type not in ProfileSuggestionType.values:
        raise ValueError(f"Unsupported suggestion type: {term_type}")

    strict_known_only = (
        term_type == ProfileSuggestionType.ROLE.value and not preserve_unknown_roles
    ) or (
        term_type == ProfileSuggestionType.INTEREST.value and not preserve_unknown
    )
    normalized_to_canonical = {}
    for row in _active_suggestion_rows(term_type):
        for key in _alias_keys(row):
            normalized_to_canonical[key] = row["canonical"]

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = clean_display_text(value, max_length=160)
        key = normalize_lookup_key(text)
        if not key or _cross_type_known(term_type, key):
            continue

        canonical = _dictionary_canonical(term_type, key) or normalized_to_canonical.get(key)
        if canonical is None:
            if strict_known_only or not preserve_unknown or is_rejected_profile_term(term_type, text):
                continue
            canonical = text

        canonical_key = normalize_lookup_key(canonical)
        if not canonical_key or canonical_key in seen:
            continue
        seen.add(canonical_key)
        cleaned.append(canonical)
    return cleaned


__all__ = [
    "FUZZY_THRESHOLD",
    "MIN_CONFIDENCE",
    "MIN_INTEREST_FREQUENCY",
    "MIN_ROLE_FREQUENCY",
    "MIN_SKILL_FREQUENCY",
    "coerce_limit",
    "normalize_profile_terms",
    "sanitize_query_input",
    "suggest_profile_terms",
]
