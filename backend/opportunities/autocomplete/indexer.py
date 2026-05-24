from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from opportunities.extraction.profile_terms import (
    INTEREST_ALIAS_MAP,
    ROLE_ALIAS_MAP,
    ExtractedProfileTerm,
    extract_profile_terms,
)
from opportunities.models import Opportunite, ProfileSuggestion, ProfileSuggestionType, StatutOpportunite
from opportunities.normalization.text import dedupe_texts, normalize_lookup_key


DEFAULT_MIN_FREQUENCY = {
    ProfileSuggestionType.SKILL.value: int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_SKILL_FREQUENCY", 2)),
    ProfileSuggestionType.ROLE.value: int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_ROLE_FREQUENCY", 2)),
    ProfileSuggestionType.INTEREST.value: int(getattr(settings, "PROFILE_AUTOCOMPLETE_MIN_INTEREST_FREQUENCY", 1)),
}
PROFILE_SUGGESTION_CACHE_KEYS = (
    f"profile_suggestions:v3:{ProfileSuggestionType.SKILL.value}",
    f"profile_suggestions:v3:{ProfileSuggestionType.ROLE.value}",
    f"profile_suggestions:v3:{ProfileSuggestionType.INTEREST.value}",
)


def _term_type_value(value: str) -> str:
    return value.value if hasattr(value, "value") else str(value)


@dataclass
class AggregatedTerm:
    term_type: str
    canonical: str
    aliases: list[str] = field(default_factory=list)
    opportunity_ids: set[int] = field(default_factory=set)
    confidence_total: float = 0.0
    occurrences: int = 0
    language_counts: Counter = field(default_factory=Counter)
    source_counts: Counter = field(default_factory=Counter)
    canonical_counts: Counter = field(default_factory=Counter)

    def add(self, term: ExtractedProfileTerm, opportunity_id: int) -> None:
        self.opportunity_ids.add(opportunity_id)
        self.aliases.extend(term.aliases)
        self.aliases.append(term.canonical)
        self.confidence_total += max(0.0, min(1.0, float(term.confidence or 0.0)))
        self.occurrences += 1
        self.language_counts[term.language or "unknown"] += 1
        self.source_counts[term.source or "unknown"] += 1
        self.canonical_counts[term.canonical] += 1

    @property
    def frequency(self) -> int:
        return len(self.opportunity_ids)

    @property
    def confidence(self) -> float:
        if not self.occurrences:
            return 0.0
        return round(self.confidence_total / self.occurrences, 4)

    @property
    def best_canonical(self) -> str:
        if not self.canonical_counts:
            return self.canonical
        return self.canonical_counts.most_common(1)[0][0]

    def merge(self, other: "AggregatedTerm") -> None:
        self.aliases.extend(other.aliases)
        self.opportunity_ids.update(other.opportunity_ids)
        self.confidence_total += other.confidence_total
        self.occurrences += other.occurrences
        self.language_counts.update(other.language_counts)
        self.source_counts.update(other.source_counts)
        self.canonical_counts.update(other.canonical_counts)


def _canonical_key(term_type: str, canonical: str) -> str:
    term_type = _term_type_value(term_type)
    key = normalize_lookup_key(canonical)
    if term_type == ProfileSuggestionType.ROLE.value:
        return key
    return key


def _base_queryset():
    return (
        Opportunite.objects.filter(statut=StatutOpportunite.ACTIVE)
        .only(
            "id",
            "titre",
            "description",
            "skills",
            "normalized_industries",
            "extra_data",
            "type_opportunite",
            "quality_score",
        )
        .order_by("id")
    )


ROLE_TOKEN_ALIAS_KEYS = {
    "frontend developer": (
        "frontend",
        "front end",
        "front-end",
        "frontend developer",
        "front end developer",
        "front-end developer",
    ),
    "backend developer": (
        "backend",
        "back end",
        "back-end",
        "backend developer",
        "back end developer",
        "back-end developer",
    ),
    "full stack developer": (
        "fullstack",
        "full stack",
        "full-stack",
        "full stack developer",
        "fullstack developer",
        "full-stack developer",
    ),
}


def _role_generated_alias_keys(canonical: str) -> list[str]:
    canonical_key = normalize_lookup_key(canonical)
    keys = list(ROLE_TOKEN_ALIAS_KEYS.get(canonical_key, ()))
    keys.extend(
        alias_key
        for alias_key, alias_canonical in ROLE_ALIAS_MAP.items()
        if normalize_lookup_key(alias_canonical) == canonical_key
    )
    return [key for key in dict.fromkeys(normalize_lookup_key(key) for key in keys) if key]


def _interest_generated_alias_keys(canonical: str) -> list[str]:
    canonical_key = normalize_lookup_key(canonical)
    keys = [
        alias_key
        for alias_key, alias_canonical in INTEREST_ALIAS_MAP.items()
        if normalize_lookup_key(alias_canonical) == canonical_key
    ]
    return [key for key in dict.fromkeys(keys) if key]


def _alias_keys(aggregate: AggregatedTerm) -> list[str]:
    if aggregate.term_type == ProfileSuggestionType.ROLE.value:
        values = [
            aggregate.best_canonical,
            *_role_generated_alias_keys(aggregate.best_canonical),
        ]
    else:
        values = [aggregate.best_canonical, *aggregate.aliases]
    keys = [normalize_lookup_key(value) for value in values]
    if aggregate.term_type == ProfileSuggestionType.INTEREST.value:
        keys.extend(_interest_generated_alias_keys(aggregate.best_canonical))
    return [
        key
        for key in dict.fromkeys(keys)
        if key
    ]


def _compact_keys(aggregate: AggregatedTerm) -> list[str]:
    return [
        compact_key
        for key in _alias_keys(aggregate)
        if (compact_key := key.replace(" ", ""))
    ]


def _token_keys(aggregate: AggregatedTerm) -> list[str]:
    tokens = []
    if aggregate.term_type == ProfileSuggestionType.ROLE.value:
        keys = [
            normalize_lookup_key(aggregate.best_canonical),
            *_role_generated_alias_keys(aggregate.best_canonical),
        ]
    else:
        keys = _alias_keys(aggregate)
    for key in keys:
        tokens.extend(key.split())
    return [token for token in dict.fromkeys(tokens) if token]


def _canonical_quality(aggregate: AggregatedTerm) -> float:
    frequency_signal = min(aggregate.frequency / 20.0, 1.0)
    source_diversity = min(len(aggregate.source_counts) / 3.0, 1.0)
    alias_diversity = min(len(_alias_keys(aggregate)) / 8.0, 1.0)
    quality = (
        aggregate.confidence * 0.62
        + frequency_signal * 0.22
        + source_diversity * 0.08
        + alias_diversity * 0.08
    )
    return round(max(0.0, min(1.0, quality)), 4)


def _merge_equivalent_aggregates(
    aggregates: dict[tuple[str, str], AggregatedTerm]
) -> dict[tuple[str, str], AggregatedTerm]:
    merged: dict[tuple[str, str], AggregatedTerm] = {}
    alias_owner: dict[tuple[str, str], tuple[str, str]] = {}

    for key, aggregate in aggregates.items():
        term_type, normalized_key = key
        semantic_keys = [normalized_key, *_alias_keys(aggregate)]
        owner_key = None
        for alias_key in semantic_keys:
            owner_key = alias_owner.get((term_type, alias_key))
            if owner_key:
                break

        if owner_key is None:
            owner_key = key
            merged[owner_key] = aggregate
        else:
            merged[owner_key].merge(aggregate)

        for alias_key in semantic_keys:
            alias_owner[(term_type, alias_key)] = owner_key

    return merged


def _invalidate_suggestion_cache() -> None:
    try:
        cache.delete_many(PROFILE_SUGGESTION_CACHE_KEYS)
    except Exception:
        pass


def build_profile_suggestion_index(
    *,
    queryset=None,
    min_frequency: dict[str, int] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Build a materialized autocomplete index from current opportunities.

    The function is deterministic and replayable. It deactivates stale terms
    instead of deleting them so previous profile values remain auditable.
    """
    queryset = queryset if queryset is not None else _base_queryset()
    min_frequency = {**DEFAULT_MIN_FREQUENCY, **(min_frequency or {})}

    aggregates: dict[tuple[str, str], AggregatedTerm] = {}
    scanned = 0

    for opportunity in queryset.iterator(chunk_size=500):
        scanned += 1
        seen_in_opportunity: set[tuple[str, str]] = set()
        for term in extract_profile_terms(opportunity):
            term_type = _term_type_value(term.term_type)
            normalized_key = _canonical_key(term_type, term.canonical)
            if not normalized_key:
                continue

            key = (term_type, normalized_key)
            if key not in aggregates:
                aggregates[key] = AggregatedTerm(
                    term_type=term_type,
                    canonical=term.canonical,
                )

            aggregates[key].add(term, opportunity.id)
            seen_in_opportunity.add(key)

        for key in seen_in_opportunity:
            aggregates[key].opportunity_ids.add(opportunity.id)

    aggregates = _merge_equivalent_aggregates(aggregates)
    kept = {
        key: aggregate
        for key, aggregate in aggregates.items()
        if aggregate.frequency >= min_frequency.get(aggregate.term_type, 1)
    }

    if dry_run:
        return {
            "scanned": scanned,
            "extracted": len(aggregates),
            "kept": len(kept),
            "by_type": dict(Counter(term_type for term_type, _key in kept)),
            "dry_run": True,
        }

    now = timezone.now()
    active_keys = set(kept.keys())
    updated = 0
    created = 0

    with transaction.atomic():
        for (term_type, normalized_key), aggregate in kept.items():
            canonical = aggregate.best_canonical
            aliases = dedupe_texts([canonical, *aggregate.aliases])
            alias_keys = _alias_keys(aggregate)
            suggestion, was_created = ProfileSuggestion.objects.update_or_create(
                term_type=term_type,
                normalized_key=normalized_key,
                defaults={
                    "canonical": canonical,
                    "aliases": aliases[:40],
                    "frequency": aggregate.frequency,
                    "confidence": aggregate.confidence,
                    "language_counts": dict(aggregate.language_counts),
                    "metadata": {
                        "canonical_key": normalize_lookup_key(canonical),
                        "alias_keys": alias_keys[:80],
                        "compact_keys": _compact_keys(aggregate)[:80],
                        "compact_alias_keys": _compact_keys(aggregate)[:80],
                        "token_keys": _token_keys(aggregate)[:80],
                        "occurrences": aggregate.occurrences,
                        "source_count": len(aggregate.source_counts),
                        "source_counts": dict(aggregate.source_counts),
                        "extraction_sources": sorted(aggregate.source_counts),
                        "quality": _canonical_quality(aggregate),
                        "frequency": aggregate.frequency,
                    },
                    "is_active": True,
                    "last_built_at": now,
                },
            )
            del suggestion
            if was_created:
                created += 1
            else:
                updated += 1

        existing_keys = set(
            ProfileSuggestion.objects.values_list("term_type", "normalized_key")
        )
        stale_keys = existing_keys - active_keys
        if stale_keys:
            stale_filters = defaultdict(list)
            for term_type, normalized_key in stale_keys:
                stale_filters[term_type].append(normalized_key)
            for term_type, keys in stale_filters.items():
                ProfileSuggestion.objects.filter(
                    term_type=term_type,
                    normalized_key__in=keys,
                ).update(is_active=False, last_built_at=now)

    _invalidate_suggestion_cache()
    return {
        "scanned": scanned,
        "extracted": len(aggregates),
        "kept": len(kept),
        "created": created,
        "updated": updated,
        "deactivated": len(stale_keys) if "stale_keys" in locals() else 0,
        "by_type": dict(Counter(term_type for term_type, _key in kept)),
        "dry_run": False,
    }


__all__ = ["build_profile_suggestion_index"]
