from __future__ import annotations

from dataclasses import dataclass

from ai.esco_mapper import normalize_text


OFFICIAL_ESCO_SKILL_URI_PREFIX = "http://data.europa.eu/esco/skill/"
EXACT_MATCH_TYPES = frozenset({"preferred_label", "alt_label", "hidden_label"})


@dataclass(frozen=True)
class StoredESCOSkillMatch:
    uri: str
    label: str
    raw_keys: tuple[str, ...]
    match_types: tuple[str, ...]

    @property
    def has_exact_match(self) -> bool:
        return any(match_type in EXACT_MATCH_TYPES for match_type in self.match_types)

    @property
    def has_semantic_match(self) -> bool:
        return "semantic" in self.match_types


@dataclass(frozen=True)
class ESCONormalizedSkillOverlap:
    shared_uris: tuple[str, ...]
    shared_labels: tuple[str, ...]
    exact_overlap_count: int
    anchored_overlap_count: int
    semantic_only_overlap_count: int
    raw_equivalent_overlap_count: int
    anchored_novel_overlap_count: int

    @property
    def has_overlap(self) -> bool:
        return bool(self.shared_uris)


def is_official_esco_skill_uri(uri: str | None) -> bool:
    return str(uri or "").strip().startswith(OFFICIAL_ESCO_SKILL_URI_PREFIX)


def _clean_match_type(value) -> str:
    return str(value or "").strip().lower()


def _clean_label(item: dict[str, object]) -> str:
    for field_name in (
        "canonical_skill_en",
        "canonical_skill_fr",
        "canonical_skill",
        "matched_label",
        "raw_skill",
    ):
        value = str(item.get(field_name) or "").strip()
        if value:
            return value
    return ""


def _clean_raw_key(item: dict[str, object], label: str) -> str:
    raw_skill = str(item.get("raw_skill") or "").strip()
    return normalize_text(raw_skill) or normalize_text(label)


def _freeze_sorted(values) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def build_stored_esco_skill_index(values) -> dict[str, StoredESCOSkillMatch]:
    if not isinstance(values, list):
        return {}

    aggregated = {}
    for item in values:
        if not isinstance(item, dict):
            continue

        uri = str(item.get("esco_uri") or "").strip()
        match_type = _clean_match_type(item.get("match_type"))
        if not is_official_esco_skill_uri(uri) or match_type == "unmatched":
            continue

        label = _clean_label(item)
        raw_key = _clean_raw_key(item, label)
        payload = aggregated.setdefault(
            uri,
            {
                "label": label,
                "raw_keys": set(),
                "match_types": set(),
            },
        )
        if label and not payload["label"]:
            payload["label"] = label
        if raw_key:
            payload["raw_keys"].add(raw_key)
        if match_type:
            payload["match_types"].add(match_type)

    return {
        uri: StoredESCOSkillMatch(
            uri=uri,
            label=payload["label"] or uri,
            raw_keys=_freeze_sorted(payload["raw_keys"]),
            match_types=_freeze_sorted(payload["match_types"]),
        )
        for uri, payload in aggregated.items()
    }


def build_esco_skill_overlap(user_values, opportunity_values) -> ESCONormalizedSkillOverlap:
    user_matches = build_stored_esco_skill_index(user_values)
    opportunity_matches = build_stored_esco_skill_index(opportunity_values)
    shared_uris = tuple(sorted(set(user_matches).intersection(opportunity_matches)))

    shared_labels = []
    exact_overlap_count = 0
    anchored_overlap_count = 0
    semantic_only_overlap_count = 0
    raw_equivalent_overlap_count = 0
    anchored_novel_overlap_count = 0

    for uri in shared_uris:
        user_match = user_matches[uri]
        opportunity_match = opportunity_matches[uri]
        shared_labels.append(opportunity_match.label or user_match.label or uri)

        both_exact = user_match.has_exact_match and opportunity_match.has_exact_match
        anchored = user_match.has_exact_match or opportunity_match.has_exact_match
        raw_equivalent = bool(set(user_match.raw_keys).intersection(opportunity_match.raw_keys))

        if both_exact:
            exact_overlap_count += 1
        if anchored:
            anchored_overlap_count += 1
        if not anchored and (user_match.has_semantic_match or opportunity_match.has_semantic_match):
            semantic_only_overlap_count += 1
        if raw_equivalent:
            raw_equivalent_overlap_count += 1
        if anchored and not raw_equivalent:
            anchored_novel_overlap_count += 1

    return ESCONormalizedSkillOverlap(
        shared_uris=shared_uris,
        shared_labels=tuple(shared_labels),
        exact_overlap_count=exact_overlap_count,
        anchored_overlap_count=anchored_overlap_count,
        semantic_only_overlap_count=semantic_only_overlap_count,
        raw_equivalent_overlap_count=raw_equivalent_overlap_count,
        anchored_novel_overlap_count=anchored_novel_overlap_count,
    )
