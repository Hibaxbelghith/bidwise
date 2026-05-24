from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional runtime acceleration
    np = None

from ai.esco_skill_embeddings import embedding_is_usable
from ai.esco_mapper import normalize_text
from ai.models import BidWiseSkillAlias, ESCOSkill


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ESCOSkillLabelRecord:
    skill_uri: str
    label: str
    label_type: str
    language: str


@dataclass(frozen=True)
class ESCOSkillRecord:
    uri: str
    preferred_label: str
    alt_labels: tuple[str, ...]
    preferred_label_en: str
    preferred_label_fr: str
    alt_labels_en: tuple[str, ...]
    alt_labels_fr: tuple[str, ...]
    hidden_labels_en: tuple[str, ...]
    hidden_labels_fr: tuple[str, ...]
    search_text_multilingual: str
    embedding: tuple[float, ...]
    embedding_model: str
    embedding_dimensions: int | None
    embedding_version: str
    embedding_updated_at: datetime | None

    @property
    def labels(self) -> tuple[str, ...]:
        return (self.preferred_label, *self.alt_labels)

    @property
    def canonical_label(self) -> str:
        return self.preferred_label_en or self.preferred_label_fr or self.preferred_label

    @property
    def exact_labels(self) -> tuple[ESCOSkillLabelRecord, ...]:
        entries = []
        entries.extend(
            _build_label_records(
                self.uri,
                "preferred_label",
                "legacy",
                [self.preferred_label],
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "preferred_label",
                "en",
                [self.preferred_label_en],
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "preferred_label",
                "fr",
                [self.preferred_label_fr],
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "alt_label",
                "legacy",
                self.alt_labels,
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "alt_label",
                "en",
                self.alt_labels_en,
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "alt_label",
                "fr",
                self.alt_labels_fr,
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "hidden_label",
                "en",
                self.hidden_labels_en,
            )
        )
        entries.extend(
            _build_label_records(
                self.uri,
                "hidden_label",
                "fr",
                self.hidden_labels_fr,
            )
        )
        return tuple(entries)


@dataclass(frozen=True)
class ESCOSemanticSpace:
    model_name: str
    model_version: str
    dimensions: int
    identifier: str
    skills: tuple[ESCOSkillRecord, ...]
    embedding_matrix: object | None = None

    @property
    def skill_count(self) -> int:
        return len(self.skills)

    def top_matches(
        self,
        query_vector: list[float] | tuple[float, ...],
        *,
        limit: int = 3,
    ) -> tuple[tuple[ESCOSkillRecord, float], ...]:
        if not self.skills or limit <= 0:
            return ()

        top_k = min(limit, len(self.skills))
        if np is not None and self.embedding_matrix is not None:
            query = np.asarray(query_vector, dtype="float32")
            scores = self.embedding_matrix @ query
            ranked_indexes = np.argsort(-scores)[:top_k]
            return tuple(
                (self.skills[int(index)], float(scores[int(index)]))
                for index in ranked_indexes
            )

        scored = []
        for skill in self.skills:
            score = sum(left * right for left, right in zip(query_vector, skill.embedding))
            scored.append((skill, float(score)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return tuple(scored[:top_k])


@dataclass(frozen=True)
class ESCOSkillIndex:
    skills: tuple[ESCOSkillRecord, ...]
    by_uri: dict[str, ESCOSkillRecord]
    by_label: dict[str, ESCOSkillRecord]
    preferred_label_matches: dict[str, tuple[ESCOSkillLabelRecord, ...]]
    alias_label_matches: dict[str, tuple[ESCOSkillLabelRecord, ...]]
    custom_alias_matches: dict[str, tuple[ESCOSkillLabelRecord, ...]]
    embedded_skills: tuple[ESCOSkillRecord, ...]
    semantic_spaces: tuple[ESCOSemanticSpace, ...]

    @property
    def total_skills(self) -> int:
        return len(self.skills)

    @property
    def embedded_skill_count(self) -> int:
        return len(self.embedded_skills)

    @property
    def is_empty(self) -> bool:
        return not self.skills


def _coerce_embedding_tuple(value) -> tuple[float, ...]:
    if value is None:
        return ()
    if hasattr(value, "tolist"):
        value = value.tolist()
    try:
        return tuple(float(item) for item in value)
    except TypeError:
        return ()


def _clean_labels(preferred_label: str, alt_labels: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    seen = set()
    cleaned = []

    for raw_value in [preferred_label, *(list(alt_labels or []))]:
        value = str(raw_value or "").strip()
        if not value:
            continue
        key = normalize_text(value)
        if not key or key in seen:
            continue
        seen.add(key)
        cleaned.append(value)

    return tuple(cleaned)


def _clean_label_group(values) -> tuple[str, ...]:
    return _clean_labels("", values)


def _build_label_records(
    skill_uri: str,
    label_type: str,
    language: str,
    labels: list[str] | tuple[str, ...] | None,
) -> list[ESCOSkillLabelRecord]:
    return [
        ESCOSkillLabelRecord(
            skill_uri=skill_uri,
            label=label,
            label_type=label_type,
            language=language,
        )
        for label in _clean_label_group(labels)
    ]


def _freeze_label_map(values: dict[str, list[ESCOSkillLabelRecord]]) -> dict[str, tuple[ESCOSkillLabelRecord, ...]]:
    return {
        key: tuple(entries)
        for key, entries in values.items()
    }


def _build_semantic_space_identifier(model_name: str, model_version: str, dimensions: int) -> str:
    return f"{model_name}@{model_version}:{dimensions}"


def build_esco_skill_embedding_text(
    preferred_label: str,
    alt_labels: list[str] | tuple[str, ...] | None = None,
    *,
    preferred_label_en: str = "",
    preferred_label_fr: str = "",
    alt_labels_en: list[str] | tuple[str, ...] | None = None,
    alt_labels_fr: list[str] | tuple[str, ...] | None = None,
    hidden_labels_en: list[str] | tuple[str, ...] | None = None,
    hidden_labels_fr: list[str] | tuple[str, ...] | None = None,
    search_text_multilingual: str = "",
) -> str:
    label_values = [
        preferred_label,
        preferred_label_en,
        preferred_label_fr,
        *list(alt_labels or []),
        *list(alt_labels_en or []),
        *list(alt_labels_fr or []),
        *list(hidden_labels_en or []),
        *list(hidden_labels_fr or []),
    ]
    if not any(str(value or "").strip() for value in label_values) and search_text_multilingual:
        label_values.append(search_text_multilingual)

    labels = _clean_labels(
        preferred_label_en or preferred_label_fr or preferred_label,
        label_values,
    )
    if not labels:
        return ""
    canonical = labels[0]
    aliases = labels[1:]
    if not aliases:
        return canonical
    return f"{canonical}\naliases: {', '.join(aliases)}"


@lru_cache(maxsize=1)
def _load_esco_skill_index() -> ESCOSkillIndex:
    try:
        rows = list(
            ESCOSkill.objects.only(
                "uri",
                "preferred_label",
                "alt_labels",
                "preferred_label_en",
                "preferred_label_fr",
                "alt_labels_en",
                "alt_labels_fr",
                "hidden_labels_en",
                "hidden_labels_fr",
                "search_text_multilingual",
                "embedding",
                "embedding_model",
                "embedding_dimensions",
                "embedding_version",
                "embedding_updated_at",
            ).order_by("preferred_label", "uri")
        )
    except Exception as exc:
        logger.warning(
            "ESCO skill index unavailable; using empty in-memory cache: %s",
            exc,
        )
        return ESCOSkillIndex(
            skills=(),
            by_uri={},
            by_label={},
            preferred_label_matches={},
            alias_label_matches={},
            custom_alias_matches={},
            embedded_skills=(),
            semantic_spaces=(),
        )

    skills = []
    by_uri = {}
    by_label = {}
    preferred_label_matches = {}
    alias_label_matches = {}
    custom_alias_matches = {}
    embedded_skills = []
    semantic_groups = {}

    for row in rows:
        cleaned_labels = _clean_labels(row.preferred_label, row.alt_labels)
        if not cleaned_labels:
            continue

        embedding = _coerce_embedding_tuple(row.embedding)
        record = ESCOSkillRecord(
            uri=row.uri,
            preferred_label=cleaned_labels[0],
            alt_labels=cleaned_labels[1:],
            preferred_label_en=str(getattr(row, "preferred_label_en", "") or "").strip(),
            preferred_label_fr=str(getattr(row, "preferred_label_fr", "") or "").strip(),
            alt_labels_en=_clean_label_group(getattr(row, "alt_labels_en", []) or []),
            alt_labels_fr=_clean_label_group(getattr(row, "alt_labels_fr", []) or []),
            hidden_labels_en=_clean_label_group(getattr(row, "hidden_labels_en", []) or []),
            hidden_labels_fr=_clean_label_group(getattr(row, "hidden_labels_fr", []) or []),
            search_text_multilingual=str(getattr(row, "search_text_multilingual", "") or "").strip(),
            embedding=embedding,
            embedding_model=str(row.embedding_model or "").strip(),
            embedding_dimensions=row.embedding_dimensions,
            embedding_version=str(row.embedding_version or "").strip(),
            embedding_updated_at=row.embedding_updated_at,
        )
        skills.append(record)
        by_uri.setdefault(record.uri, record)

        for label_entry in record.exact_labels:
            key = normalize_text(label_entry.label)
            if not key:
                continue
            by_label.setdefault(key, record)
            target_map = (
                preferred_label_matches
                if label_entry.label_type == "preferred_label"
                else alias_label_matches
            )
            target_map.setdefault(key, []).append(label_entry)

        if embedding_is_usable(record):
            embedded_skills.append(record)
            dimensions = int(record.embedding_dimensions or 0)
            identifier = _build_semantic_space_identifier(
                record.embedding_model,
                record.embedding_version,
                dimensions,
            )
            semantic_groups.setdefault(
                identifier,
                {
                    "model_name": record.embedding_model,
                    "model_version": record.embedding_version,
                    "dimensions": dimensions,
                    "skills": [],
                },
            )["skills"].append(record)

    try:
        alias_rows = list(
            BidWiseSkillAlias.objects.select_related("target_skill").filter(
                status=BidWiseSkillAlias.Status.ACTIVE
            )
        )
    except Exception as exc:
        logger.warning("BidWise skill alias index unavailable; continuing without custom aliases: %s", exc)
        alias_rows = []

    for alias_row in alias_rows:
        key = normalize_text(getattr(alias_row, "normalized_key", "") or alias_row.alias)
        if not key:
            continue
        skill = by_uri.get(getattr(alias_row.target_skill, "uri", ""))
        if skill is None:
            continue
        custom_alias_matches.setdefault(key, []).append(
            ESCOSkillLabelRecord(
                skill_uri=skill.uri,
                label=str(alias_row.alias or "").strip(),
                label_type="custom_alias",
                language=str(alias_row.language or "").strip() or "custom",
            )
        )

    semantic_spaces = []
    for identifier, payload in semantic_groups.items():
        group_skills = tuple(payload["skills"])
        embedding_matrix = None
        if np is not None and group_skills:
            embedding_matrix = np.asarray(
                [skill.embedding for skill in group_skills],
                dtype="float32",
            )
        semantic_spaces.append(
            ESCOSemanticSpace(
                model_name=payload["model_name"],
                model_version=payload["model_version"],
                dimensions=payload["dimensions"],
                identifier=identifier,
                skills=group_skills,
                embedding_matrix=embedding_matrix,
            )
        )
    semantic_spaces.sort(key=lambda item: item.skill_count, reverse=True)

    return ESCOSkillIndex(
        skills=tuple(skills),
        by_uri=by_uri,
        by_label=by_label,
        preferred_label_matches=_freeze_label_map(preferred_label_matches),
        alias_label_matches=_freeze_label_map(alias_label_matches),
        custom_alias_matches=_freeze_label_map(custom_alias_matches),
        embedded_skills=tuple(embedded_skills),
        semantic_spaces=tuple(semantic_spaces),
    )


def clear_esco_skill_index_cache() -> None:
    _load_esco_skill_index.cache_clear()


def get_esco_skill_index() -> ESCOSkillIndex:
    return _load_esco_skill_index()


def get_esco_skill_by_uri(uri: str) -> ESCOSkillRecord | None:
    value = str(uri or "").strip()
    if not value:
        return None
    return get_esco_skill_index().by_uri.get(value)


def find_esco_skill_by_label(label: str) -> ESCOSkillRecord | None:
    key = normalize_text(label)
    if not key:
        return None
    return get_esco_skill_index().by_label.get(key)
