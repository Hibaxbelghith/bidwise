from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass

from ai.esco_mapper import normalize_text
from ai.esco_skill_embeddings import (
    ESCOSkillEmbeddingValidationError,
    build_embedding_metadata,
    validate_embedding_shape,
)
from ai.esco_skill_index import (
    ESCOSemanticSpace,
    ESCOSkillIndex,
    ESCOSkillLabelRecord,
    ESCOSkillRecord,
    get_esco_skill_index,
)
from opportunities.embeddings import service as embedding_service


logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.72
DEFAULT_MAX_CANDIDATES = 3
SEMANTIC_AMBIGUITY_MARGIN = 0.02
MIN_SEMANTIC_QUERY_LENGTH = 4
MIN_OVERLAP_TOKEN_LENGTH = 4
MIN_SUBSTRING_BRIDGE_LENGTH = 5


@dataclass(frozen=True)
class ESCOSkillNormalizationResult:
    raw_skill: str
    canonical_skill: str | None
    esco_uri: str | None
    match_type: str
    similarity: float | None = None
    embedding_model: str | None = None
    embedding_version: str | None = None
    embedding_dimensions: int | None = None
    language: str | None = None
    matched_label: str | None = None
    canonical_skill_en: str | None = None
    canonical_skill_fr: str | None = None
    unmatched_reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class _PendingSkill:
    raw_skill: str
    normalized_key: str


def _normalize_raw_skill(value) -> str:
    return str(value or "").replace("\x00", " ").replace("\ufeff", " ").strip()


def _compact_key(value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    return re.sub(r"[^a-z0-9]", "", normalized)


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in normalize_text(value).split()
        if len(token) >= MIN_OVERLAP_TOKEN_LENGTH
    }


def _unique_skill_records(
    index: ESCOSkillIndex,
    label_records: tuple[ESCOSkillLabelRecord, ...] | list[ESCOSkillLabelRecord],
) -> tuple[tuple[ESCOSkillRecord, ESCOSkillLabelRecord], ...]:
    priority_map = {
        "en": 0,
        "fr": 1,
        "legacy": 2,
    }
    selected = {}
    for label_record in label_records:
        skill_record = index.by_uri.get(label_record.skill_uri)
        if skill_record is None:
            continue
        current = selected.get(label_record.skill_uri)
        if current is None:
            selected[label_record.skill_uri] = (skill_record, label_record)
            continue
        _, current_label_record = current
        if priority_map.get(label_record.language, 99) < priority_map.get(current_label_record.language, 99):
            selected[label_record.skill_uri] = (skill_record, label_record)
    return tuple(selected.values())


def _is_official_esco_uri(uri: str) -> bool:
    return str(uri or "").startswith("http://data.europa.eu/esco/")


def _resolve_unique_exact_candidate(
    matches: tuple[tuple[ESCOSkillRecord, ESCOSkillLabelRecord], ...],
) -> tuple[tuple[ESCOSkillRecord, ESCOSkillLabelRecord] | None, bool]:
    if len(matches) == 1:
        return matches[0], False
    if len(matches) <= 1:
        return None, False

    official_matches = [match for match in matches if _is_official_esco_uri(match[0].uri)]
    if len(official_matches) == 1:
        return official_matches[0], False
    return None, True


def _promote_official_alias_over_legacy_preferred(
    preferred_match: tuple[ESCOSkillRecord, ESCOSkillLabelRecord] | None,
    alias_match: tuple[ESCOSkillRecord, ESCOSkillLabelRecord] | None,
) -> tuple[ESCOSkillRecord, ESCOSkillLabelRecord] | None:
    if preferred_match is None or alias_match is None:
        return None

    preferred_skill, _preferred_label = preferred_match
    alias_skill, alias_label = alias_match
    if _is_official_esco_uri(preferred_skill.uri):
        return None
    if not _is_official_esco_uri(alias_skill.uri):
        return None
    if alias_label.label_type != "alt_label":
        return None
    return alias_match


def _result_from_exact_match(
    raw_skill: str,
    skill_record: ESCOSkillRecord,
    label_record: ESCOSkillLabelRecord,
) -> ESCOSkillNormalizationResult:
    return ESCOSkillNormalizationResult(
        raw_skill=raw_skill,
        canonical_skill=skill_record.canonical_label,
        canonical_skill_en=skill_record.preferred_label_en or None,
        canonical_skill_fr=skill_record.preferred_label_fr or None,
        esco_uri=skill_record.uri,
        match_type=label_record.label_type,
        similarity=1.0,
        language=label_record.language,
        matched_label=label_record.label,
    )


def _unmatched_result(
    raw_skill: str,
    *,
    reason: str = "unmatched",
) -> ESCOSkillNormalizationResult:
    return ESCOSkillNormalizationResult(
        raw_skill=raw_skill,
        canonical_skill=None,
        canonical_skill_en=None,
        canonical_skill_fr=None,
        esco_uri=None,
        match_type="unmatched",
        unmatched_reason=reason,
    )


def _surface_bridge_exists(raw_skill: str, skill_record: ESCOSkillRecord) -> bool:
    raw_normalized = normalize_text(raw_skill)
    raw_compact = _compact_key(raw_skill)
    raw_tokens = _tokenize(raw_skill)

    for label in (
        skill_record.preferred_label,
        skill_record.preferred_label_en,
        skill_record.preferred_label_fr,
        *skill_record.alt_labels,
        *skill_record.alt_labels_en,
        *skill_record.alt_labels_fr,
        *skill_record.hidden_labels_en,
        *skill_record.hidden_labels_fr,
    ):
        normalized_label = normalize_text(label)
        compact_label = _compact_key(label)
        if raw_normalized and raw_normalized == normalized_label:
            return True
        if raw_compact and raw_compact == compact_label:
            return True
        if (
            raw_compact
            and compact_label
            and min(len(raw_compact), len(compact_label)) >= MIN_SUBSTRING_BRIDGE_LENGTH
            and (raw_compact in compact_label or compact_label in raw_compact)
        ):
            return True
        if raw_tokens and raw_tokens.intersection(_tokenize(label)):
            return True

    return False


def _pick_semantic_space(index: ESCOSkillIndex) -> ESCOSemanticSpace | None:
    spaces = index.semantic_spaces
    if not spaces:
        return None

    try:
        default_metadata = build_embedding_metadata()
    except ESCOSkillEmbeddingValidationError as exc:
        logger.warning("Unable to resolve default ESCO normalization embedding space: %s", exc)
        default_metadata = None

    if default_metadata is not None:
        default_identifier = f"{default_metadata['identifier']}:{default_metadata['dimensions']}"
        for space in spaces:
            if space.identifier == default_identifier:
                return space

    if len(spaces) == 1:
        return spaces[0]

    logger.warning(
        "Skipping semantic ESCO skill matching because multiple embedding spaces are present "
        "and none matches the default runtime metadata."
    )
    return None


def _semantic_query_is_allowed(raw_skill: str) -> bool:
    compact = _compact_key(raw_skill)
    return len(compact) >= MIN_SEMANTIC_QUERY_LENGTH


def _semantic_match_result(
    raw_skill: str,
    skill_record: ESCOSkillRecord,
    similarity: float,
    semantic_space: ESCOSemanticSpace,
) -> ESCOSkillNormalizationResult:
    return ESCOSkillNormalizationResult(
        raw_skill=raw_skill,
        canonical_skill=skill_record.canonical_label,
        canonical_skill_en=skill_record.preferred_label_en or None,
        canonical_skill_fr=skill_record.preferred_label_fr or None,
        esco_uri=skill_record.uri,
        match_type="semantic",
        similarity=round(float(similarity), 6),
        embedding_model=semantic_space.model_name,
        embedding_version=semantic_space.model_version,
        embedding_dimensions=semantic_space.dimensions,
        language="multilingual",
        matched_label=skill_record.canonical_label,
    )


def _resolve_semantic_match(
    raw_skill: str,
    query_vector: list[float],
    *,
    semantic_space: ESCOSemanticSpace,
    similarity_threshold: float,
    max_candidates: int,
) -> ESCOSkillNormalizationResult:
    candidates = semantic_space.top_matches(query_vector, limit=max_candidates)
    if not candidates:
        return _unmatched_result(raw_skill, reason="semantic_no_candidates")

    best_skill, best_score = candidates[0]
    if best_score < similarity_threshold:
        return _unmatched_result(raw_skill, reason="semantic_below_threshold")
    if not _surface_bridge_exists(raw_skill, best_skill):
        return _unmatched_result(raw_skill, reason="semantic_surface_bridge_missing")

    if len(candidates) > 1:
        runner_up_skill, runner_up_score = candidates[1]
        if (
            runner_up_skill.uri != best_skill.uri
            and runner_up_score >= similarity_threshold
            and (best_score - runner_up_score) < SEMANTIC_AMBIGUITY_MARGIN
        ):
            return _unmatched_result(raw_skill, reason="semantic_ambiguous")

    return _semantic_match_result(
        raw_skill,
        best_skill,
        best_score,
        semantic_space,
    )


def _resolve_exact_match(
    raw_skill: str,
    normalized_key: str,
    index: ESCOSkillIndex,
) -> ESCOSkillNormalizationResult | None:
    preferred_matches = _unique_skill_records(
        index,
        index.preferred_label_matches.get(normalized_key, ()),
    )
    alias_matches = _unique_skill_records(
        index,
        index.alias_label_matches.get(normalized_key, ()),
    )
    custom_alias_matches = _unique_skill_records(
        index,
        index.custom_alias_matches.get(normalized_key, ()),
    )

    preferred_candidate, preferred_ambiguous = _resolve_unique_exact_candidate(preferred_matches)
    alias_candidate, alias_ambiguous = _resolve_unique_exact_candidate(alias_matches)
    custom_alias_candidate, custom_alias_ambiguous = _resolve_unique_exact_candidate(custom_alias_matches)

    promoted_alias_candidate = _promote_official_alias_over_legacy_preferred(
        preferred_candidate,
        alias_candidate,
    )
    if promoted_alias_candidate is not None:
        skill_record, label_record = promoted_alias_candidate
        return _result_from_exact_match(raw_skill, skill_record, label_record)

    if preferred_candidate is not None:
        skill_record, label_record = preferred_candidate
        return _result_from_exact_match(raw_skill, skill_record, label_record)
    if preferred_ambiguous:
        return _unmatched_result(raw_skill, reason="ambiguous_exact_match")

    if alias_candidate is not None:
        skill_record, label_record = alias_candidate
        return _result_from_exact_match(raw_skill, skill_record, label_record)
    if alias_ambiguous:
        return _unmatched_result(raw_skill, reason="ambiguous_exact_match")

    if custom_alias_candidate is not None:
        skill_record, label_record = custom_alias_candidate
        return _result_from_exact_match(raw_skill, skill_record, label_record)
    if custom_alias_ambiguous:
        return _unmatched_result(raw_skill, reason="ambiguous_exact_match")

    return None


def normalize_skills_to_esco(
    raw_skills: list[str],
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> list[ESCOSkillNormalizationResult]:
    if not raw_skills:
        return []

    threshold = float(similarity_threshold)
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("similarity_threshold must be between 0.0 and 1.0.")
    candidate_limit = max(1, int(max_candidates))

    index = get_esco_skill_index()
    if index.is_empty:
        return [
            _unmatched_result(_normalize_raw_skill(skill), reason="index_unavailable")
            for skill in raw_skills
            if _normalize_raw_skill(skill)
        ]

    unique_pending = []
    results_by_key = {}

    for item in raw_skills:
        raw_skill = _normalize_raw_skill(item)
        if not raw_skill:
            continue
        normalized_key = normalize_text(raw_skill)
        if not normalized_key or normalized_key in results_by_key:
            continue

        exact_match = _resolve_exact_match(raw_skill, normalized_key, index)
        if exact_match is not None:
            results_by_key[normalized_key] = exact_match
            continue

        unique_pending.append(
            _PendingSkill(
                raw_skill=raw_skill,
                normalized_key=normalized_key,
            )
        )

    semantic_space = _pick_semantic_space(index)
    semantic_pending = [
        pending
        for pending in unique_pending
        if pending.normalized_key not in results_by_key and _semantic_query_is_allowed(pending.raw_skill)
    ]
    unmatched_pending = [
        pending
        for pending in unique_pending
        if pending.normalized_key not in results_by_key and not _semantic_query_is_allowed(pending.raw_skill)
    ]

    if semantic_pending and semantic_space is not None:
        query_texts = [pending.raw_skill for pending in semantic_pending]
        try:
            vectors = embedding_service.generate_embeddings_batch(
                query_texts,
                model_name=semantic_space.model_name,
                batch_size=min(len(query_texts), embedding_service.DEFAULT_BATCH_SIZE),
            )
        except Exception as exc:  # noqa: BLE001 - keep normalization fail-soft
            logger.warning("ESCO semantic normalization batch embedding failed: %s", exc)
            vectors = []

        if len(vectors) == len(query_texts):
            for pending, vector in zip(semantic_pending, vectors):
                try:
                    validated_vector = validate_embedding_shape(
                        vector,
                        expected_dimensions=semantic_space.dimensions,
                    )
                except ESCOSkillEmbeddingValidationError:
                    results_by_key[pending.normalized_key] = _unmatched_result(
                        pending.raw_skill,
                        reason="invalid_query_vector",
                    )
                    continue

                results_by_key[pending.normalized_key] = _resolve_semantic_match(
                    pending.raw_skill,
                    validated_vector,
                    semantic_space=semantic_space,
                    similarity_threshold=threshold,
                    max_candidates=candidate_limit,
                )
        else:
            logger.warning(
                "ESCO semantic normalization ignored invalid embedding batch result "
                "(expected=%s, got=%s).",
                len(query_texts),
                len(vectors),
            )
            for pending in semantic_pending:
                results_by_key.setdefault(
                    pending.normalized_key,
                    _unmatched_result(pending.raw_skill, reason="semantic_embedding_batch_invalid"),
                )

    for pending in unmatched_pending:
        results_by_key.setdefault(
            pending.normalized_key,
            _unmatched_result(pending.raw_skill, reason="query_too_short_for_semantic"),
        )
    for pending in semantic_pending:
        results_by_key.setdefault(
            pending.normalized_key,
            _unmatched_result(pending.raw_skill, reason="semantic_match_not_found"),
        )

    ordered_results = []
    seen = set()
    for item in raw_skills:
        raw_skill = _normalize_raw_skill(item)
        normalized_key = normalize_text(raw_skill)
        if not raw_skill or not normalized_key or normalized_key in seen:
            continue
        seen.add(normalized_key)
        ordered_results.append(
            results_by_key.get(
                normalized_key,
                _unmatched_result(raw_skill, reason="match_resolution_missing"),
            )
        )
    return ordered_results
