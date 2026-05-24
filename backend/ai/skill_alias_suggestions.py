from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ai.esco_mapper import normalize_text
from ai.esco_skill_embeddings import (
    ESCOSkillEmbeddingValidationError,
    build_embedding_metadata,
    validate_embedding_shape,
)
from ai.esco_skill_index import ESCOSemanticSpace, get_esco_skill_index
from opportunities.embeddings import service as embedding_service
from opportunities.models import Opportunite
from users.models import Profil, ProfileResume


TARGET_ALL = "all"
TARGET_OPPORTUNITIES = "opportunities"
TARGET_PROFILES = "profiles"
TARGET_RESUMES = "resumes"
VALID_TARGETS = {
    TARGET_ALL,
    TARGET_OPPORTUNITIES,
    TARGET_PROFILES,
    TARGET_RESUMES,
}

MIN_SEMANTIC_SUGGESTION_SCORE = 0.58
STRONG_SEMANTIC_SUGGESTION_SCORE = 0.72
MAX_REVIEW_TEXT_LENGTH = 160
MIN_ALIAS_BRIDGE_TOKEN_LENGTH = 4

GENERIC_NOISE_TERMS = {
    "api",
    "backend",
    "build",
    "client",
    "clients",
    "create",
    "created",
    "deliver",
    "drive",
    "etre",
    "force",
    "gestion",
    "mission",
    "missions",
    "opportunite",
    "opportunites",
    "profile",
    "project",
    "projects",
    "proposer",
    "software",
    "travail",
}
NOISE_REASONS = {
    "generic_business_term",
    "generic_noise_term",
    "phrase_fragment",
    "phrase_too_long",
    "sentence_like_fragment",
    "too_short",
}
AMBIGUOUS_REASONS = {
    "ambiguous_exact_match",
    "query_too_short_for_semantic",
    "semantic_ambiguous",
}
LOW_SIGNAL_REASONS = {
    "semantic_below_threshold",
    "semantic_surface_bridge_missing",
}


@dataclass
class _AggregatedUnmatchedSkill:
    normalized_key: str
    display_label: str
    total_count: int = 0
    source_counts: Counter = field(default_factory=Counter)
    unmatched_reason_counts: Counter = field(default_factory=Counter)
    raw_variants: Counter = field(default_factory=Counter)

    def register(self, *, raw_skill: str, source: str, unmatched_reason: str) -> None:
        self.total_count += 1
        self.source_counts[source] += 1
        self.raw_variants[raw_skill] += 1
        if unmatched_reason:
            self.unmatched_reason_counts[unmatched_reason] += 1
        if self.raw_variants[raw_skill] > self.raw_variants[self.display_label]:
            self.display_label = raw_skill


@dataclass(frozen=True)
class SkillAliasSuggestion:
    raw_skill: str
    normalized_key: str
    total_count: int
    source_breakdown: dict[str, int]
    unmatched_reason_breakdown: dict[str, int]
    raw_variants: list[str]
    recommended_action: str
    suggestion_method: str
    top_candidate_esco_uri: str | None
    top_candidate_label: str | None
    top_candidate_language: str | None
    top_candidate_similarity: float | None
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _clean_text(value: Any) -> str:
    text = str(value or "").replace("\x00", " ").replace("\ufeff", " ").strip()
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    if len(text) > MAX_REVIEW_TEXT_LENGTH:
        text = text[:MAX_REVIEW_TEXT_LENGTH].rstrip()
    return text


def _compact_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_text(value))


def _token_count(value: str) -> int:
    return len([token for token in normalize_text(value).split() if token])


def _surface_bridge_exists(raw_skill: str, candidate_labels: list[str]) -> bool:
    raw_normalized = normalize_text(raw_skill)
    raw_compact = _compact_key(raw_skill)
    raw_tokens = {
        token
        for token in raw_normalized.split()
        if len(token) >= MIN_ALIAS_BRIDGE_TOKEN_LENGTH
    }

    for label in candidate_labels:
        label_normalized = normalize_text(label)
        label_compact = _compact_key(label)
        if raw_normalized and raw_normalized == label_normalized:
            return True
        if raw_compact and raw_compact == label_compact:
            return True
        if raw_compact and label_compact and (
            raw_compact in label_compact or label_compact in raw_compact
        ):
            return True
        label_tokens = {
            token
            for token in label_normalized.split()
            if len(token) >= MIN_ALIAS_BRIDGE_TOKEN_LENGTH
        }
        if raw_tokens and raw_tokens.intersection(label_tokens):
            return True
    return False


def _iter_unmatched_entries_for_target(
    target: str,
    *,
    chunk_size: int,
    limit: int | None,
):
    if target == TARGET_OPPORTUNITIES:
        queryset = Opportunite.objects.only("id", "normalized_skills").order_by("pk")
        field_name = "normalized_skills"
    elif target == TARGET_PROFILES:
        queryset = Profil.objects.only("id", "normalized_skills").order_by("pk")
        field_name = "normalized_skills"
    elif target == TARGET_RESUMES:
        queryset = ProfileResume.objects.only("id", "extracted_normalized_skills").order_by("pk")
        field_name = "extracted_normalized_skills"
    else:
        raise ValueError(f"Unsupported target: {target}")

    remaining = None if limit is None else max(0, int(limit))
    last_pk = None
    safe_chunk_size = max(1, int(chunk_size or 200))

    while True:
        batch_queryset = queryset
        if last_pk is not None:
            batch_queryset = batch_queryset.filter(pk__gt=last_pk)
        if remaining is not None:
            if remaining <= 0:
                break
            batch_queryset = batch_queryset[: min(safe_chunk_size, remaining)]
        else:
            batch_queryset = batch_queryset[:safe_chunk_size]

        rows = list(batch_queryset)
        if not rows:
            break

        for row in rows:
            for entry in list(getattr(row, field_name, []) or []):
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("esco_uri") or "").strip():
                    continue
                raw_skill = _clean_text(entry.get("raw_skill"))
                if not raw_skill:
                    continue
                yield {
                    "raw_skill": raw_skill,
                    "source": target,
                    "unmatched_reason": str(entry.get("unmatched_reason") or "").strip(),
                }

        last_pk = rows[-1].pk
        if remaining is not None:
            remaining -= len(rows)


def _aggregate_unmatched_skills(
    *,
    target: str,
    chunk_size: int,
    limit: int | None,
) -> list[_AggregatedUnmatchedSkill]:
    selected_targets = (
        [TARGET_OPPORTUNITIES, TARGET_PROFILES, TARGET_RESUMES]
        if target == TARGET_ALL
        else [target]
    )
    aggregated: dict[str, _AggregatedUnmatchedSkill] = {}
    for selected_target in selected_targets:
        for item in _iter_unmatched_entries_for_target(
            selected_target,
            chunk_size=chunk_size,
            limit=limit,
        ):
            raw_skill = item["raw_skill"]
            normalized_key = normalize_text(raw_skill)
            if not normalized_key:
                continue
            bucket = aggregated.get(normalized_key)
            if bucket is None:
                bucket = _AggregatedUnmatchedSkill(
                    normalized_key=normalized_key,
                    display_label=raw_skill,
                )
                aggregated[normalized_key] = bucket
            bucket.register(
                raw_skill=raw_skill,
                source=item["source"],
                unmatched_reason=item["unmatched_reason"],
            )

    rows = list(aggregated.values())
    rows.sort(key=lambda item: (-item.total_count, item.display_label.casefold()))
    return rows


def _is_probable_noise(skill: _AggregatedUnmatchedSkill) -> bool:
    normalized_key = skill.normalized_key
    compact = _compact_key(skill.display_label)
    reasons = set(skill.unmatched_reason_counts.keys())
    if compact and len(compact) <= 1:
        return True
    if normalized_key in GENERIC_NOISE_TERMS:
        return True
    if _token_count(skill.display_label) >= 6:
        return True
    if reasons and reasons.issubset(NOISE_REASONS):
        return True
    return False


def _pick_semantic_space() -> ESCOSemanticSpace | None:
    index = get_esco_skill_index()
    if index.is_empty or not index.semantic_spaces:
        return None
    try:
        default_metadata = build_embedding_metadata()
    except ESCOSkillEmbeddingValidationError:
        default_metadata = None
    if default_metadata is not None:
        identifier = f"{default_metadata['identifier']}:{default_metadata['dimensions']}"
        for space in index.semantic_spaces:
            if space.identifier == identifier:
                return space
    if len(index.semantic_spaces) == 1:
        return index.semantic_spaces[0]
    return None


def _resolve_exact_suggestion(raw_skill: str):
    index = get_esco_skill_index()
    key = normalize_text(raw_skill)
    preferred_matches = index.preferred_label_matches.get(key, ())
    if len(preferred_matches) == 1:
        label_record = preferred_matches[0]
        skill = index.by_uri.get(label_record.skill_uri)
        if skill is not None:
            return {
                "recommended_action": "official_match",
                "suggestion_method": label_record.label_type,
                "top_candidate_esco_uri": skill.uri,
                "top_candidate_label": skill.canonical_label,
                "top_candidate_language": label_record.language,
                "top_candidate_similarity": 1.0,
                "notes": "Current ESCO exact match already exists; likely stale stored unmatched data.",
            }
    alias_matches = index.alias_label_matches.get(key, ())
    if len(alias_matches) == 1:
        label_record = alias_matches[0]
        skill = index.by_uri.get(label_record.skill_uri)
        if skill is not None:
            return {
                "recommended_action": "official_match",
                "suggestion_method": label_record.label_type,
                "top_candidate_esco_uri": skill.uri,
                "top_candidate_label": skill.canonical_label,
                "top_candidate_language": label_record.language,
                "top_candidate_similarity": 1.0,
                "notes": "Current ESCO alias match already exists; likely stale stored unmatched data.",
            }
    if len(preferred_matches) > 1 or len(alias_matches) > 1:
        return {
            "recommended_action": "ambiguous",
            "suggestion_method": "ambiguous_exact_match",
            "top_candidate_esco_uri": None,
            "top_candidate_label": None,
            "top_candidate_language": None,
            "top_candidate_similarity": None,
            "notes": "Multiple ESCO exact matches exist for this surface form.",
        }
    return None


def _semantic_suggestions(
    skills: list[_AggregatedUnmatchedSkill],
    *,
    candidate_limit: int,
) -> dict[str, dict[str, object]]:
    semantic_space = _pick_semantic_space()
    if semantic_space is None or not skills:
        return {}

    texts = [item.display_label for item in skills]
    try:
        vectors = embedding_service.generate_embeddings_batch(
            texts,
            model_name=semantic_space.model_name,
            batch_size=min(len(texts), embedding_service.DEFAULT_BATCH_SIZE),
        )
    except Exception:
        return {}

    if len(vectors) != len(texts):
        return {}

    suggestions: dict[str, dict[str, object]] = {}
    for item, vector in zip(skills, vectors):
        try:
            validated_vector = validate_embedding_shape(
                vector,
                expected_dimensions=semantic_space.dimensions,
            )
        except ESCOSkillEmbeddingValidationError:
            continue

        candidates = semantic_space.top_matches(validated_vector, limit=max(1, candidate_limit))
        if not candidates:
            continue

        best_skill, best_score = candidates[0]
        if best_score < MIN_SEMANTIC_SUGGESTION_SCORE:
            continue

        candidate_labels = [
            best_skill.preferred_label,
            best_skill.preferred_label_en,
            best_skill.preferred_label_fr,
            *list(best_skill.alt_labels),
            *list(best_skill.alt_labels_en),
            *list(best_skill.alt_labels_fr),
            *list(best_skill.hidden_labels_en),
            *list(best_skill.hidden_labels_fr),
        ]
        has_surface_bridge = _surface_bridge_exists(item.display_label, candidate_labels)

        recommended_action = (
            "custom_alias_candidate"
            if (
                best_score >= STRONG_SEMANTIC_SUGGESTION_SCORE
                and _token_count(item.display_label) <= 4
                and has_surface_bridge
            )
            else "needs_review"
        )
        suggestions[item.normalized_key] = {
            "recommended_action": recommended_action,
            "suggestion_method": "semantic_nearest_neighbor",
            "top_candidate_esco_uri": best_skill.uri,
            "top_candidate_label": best_skill.canonical_label,
            "top_candidate_language": "multilingual",
            "top_candidate_similarity": round(float(best_score), 6),
            "notes": (
                "Strong semantic candidate for alias review."
                if recommended_action == "custom_alias_candidate"
                else (
                    "Semantic candidate exists but lacks enough surface evidence for automatic alias suggestion."
                    if not has_surface_bridge
                    else "Semantic candidate exists but should be reviewed manually."
                )
            ),
        }
    return suggestions


def build_skill_alias_suggestions(
    *,
    target: str = TARGET_ALL,
    top_n: int = 200,
    min_count: int = 2,
    chunk_size: int = 200,
    scan_limit: int | None = None,
    semantic_candidate_limit: int = 3,
) -> list[SkillAliasSuggestion]:
    if target not in VALID_TARGETS:
        raise ValueError(f"Unsupported target: {target}")

    aggregated = _aggregate_unmatched_skills(
        target=target,
        chunk_size=chunk_size,
        limit=scan_limit,
    )
    filtered = [
        item
        for item in aggregated
        if item.total_count >= max(1, int(min_count or 1))
    ][: max(0, int(top_n or 0))]

    exact_payloads = {
        item.normalized_key: _resolve_exact_suggestion(item.display_label)
        for item in filtered
    }
    semantic_candidates = [
        item
        for item in filtered
        if exact_payloads.get(item.normalized_key) is None and not _is_probable_noise(item)
    ]
    semantic_payloads = _semantic_suggestions(
        semantic_candidates,
        candidate_limit=max(1, int(semantic_candidate_limit or 3)),
    )

    suggestions = []
    for item in filtered:
        payload = exact_payloads.get(item.normalized_key)
        if payload is None:
            if _is_probable_noise(item):
                payload = {
                    "recommended_action": "noise",
                    "suggestion_method": "heuristic_noise_filter",
                    "top_candidate_esco_uri": None,
                    "top_candidate_label": None,
                    "top_candidate_language": None,
                    "top_candidate_similarity": None,
                    "notes": "High-frequency unmatched entry looks like noise or a generic phrase.",
                }
            elif set(item.unmatched_reason_counts.keys()).intersection(AMBIGUOUS_REASONS):
                payload = {
                    "recommended_action": "ambiguous",
                    "suggestion_method": "unmatched_reason_analysis",
                    "top_candidate_esco_uri": None,
                    "top_candidate_label": None,
                    "top_candidate_language": None,
                    "top_candidate_similarity": None,
                    "notes": "Needs manual review because current ESCO matching is ambiguous.",
                }
            else:
                payload = semantic_payloads.get(item.normalized_key) or {
                    "recommended_action": "needs_review",
                    "suggestion_method": "frequency_only",
                    "top_candidate_esco_uri": None,
                    "top_candidate_label": None,
                    "top_candidate_language": None,
                    "top_candidate_similarity": None,
                    "notes": "Frequent unmatched entry with no strong current ESCO candidate.",
                }

        suggestions.append(
            SkillAliasSuggestion(
                raw_skill=item.display_label,
                normalized_key=item.normalized_key,
                total_count=item.total_count,
                source_breakdown=dict(item.source_counts),
                unmatched_reason_breakdown=dict(item.unmatched_reason_counts),
                raw_variants=[
                    label
                    for label, _count in item.raw_variants.most_common(5)
                ],
                recommended_action=str(payload["recommended_action"]),
                suggestion_method=str(payload["suggestion_method"]),
                top_candidate_esco_uri=payload["top_candidate_esco_uri"],
                top_candidate_label=payload["top_candidate_label"],
                top_candidate_language=payload["top_candidate_language"],
                top_candidate_similarity=payload["top_candidate_similarity"],
                notes=str(payload["notes"] or ""),
            )
        )
    return suggestions


def write_skill_alias_suggestions_csv(path: str | Path, suggestions: list[SkillAliasSuggestion]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "raw_skill",
                "normalized_key",
                "total_count",
                "source_breakdown",
                "unmatched_reason_breakdown",
                "raw_variants",
                "recommended_action",
                "suggestion_method",
                "top_candidate_esco_uri",
                "top_candidate_label",
                "top_candidate_language",
                "top_candidate_similarity",
                "notes",
            ],
        )
        writer.writeheader()
        for suggestion in suggestions:
            row = suggestion.as_dict()
            row["source_breakdown"] = str(row["source_breakdown"])
            row["unmatched_reason_breakdown"] = str(row["unmatched_reason_breakdown"])
            row["raw_variants"] = " | ".join(row["raw_variants"])
            writer.writerow(row)
    return output_path


def summarize_skill_alias_suggestions(
    suggestions: list[SkillAliasSuggestion],
) -> dict[str, object]:
    action_counts = Counter(item.recommended_action for item in suggestions)
    return {
        "total_suggestions": len(suggestions),
        "action_breakdown": dict(action_counts),
        "top_actions": [
            {"action": action, "count": count}
            for action, count in action_counts.most_common()
        ],
    }
