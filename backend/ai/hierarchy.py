from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata
from typing import Any


DEFAULT_LEVEL = 2
MAX_LEVEL = 5


@dataclass(frozen=True)
class HierarchySignal:
    seniority: int = DEFAULT_LEVEL
    qualification: int = DEFAULT_LEVEL
    responsibility: int = DEFAULT_LEVEL
    seniority_terms: tuple[str, ...] = ()
    qualification_terms: tuple[str, ...] = ()
    responsibility_terms: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HierarchyValidation:
    method: str
    score_multiplier: float
    hierarchy_issue: str
    reason: str
    needs_llm: bool
    seniority_gap: int
    qualification_gap: int
    responsibility_gap: int
    profile_signal: HierarchySignal
    opportunity_signal: HierarchySignal

    @property
    def is_compatible(self) -> bool:
        return self.hierarchy_issue == "none" and self.score_multiplier >= 0.85

    def as_debug(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["is_compatible"] = self.is_compatible
        return {"hierarchy_validation": payload}


SENIORITY_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("chief technology officer", 5),
    ("directeur", 5),
    ("director", 5),
    ("architecte", 5),
    ("architect", 5),
    ("expert", 5),
    ("principal", 4),
    ("staff", 4),
    ("tech lead", 4),
    ("team lead", 4),
    ("lead", 4),
    ("mid senior", 3),
    ("mid-senior", 3),
    ("senior", 3),
    ("senior", 3),
    ("sr", 3),
    ("confirme", 2),
    ("confirmed", 2),
    ("experimente", 2),
    ("experienced", 2),
    ("intermediaire", 2),
    ("junior", 1),
    ("debutant", 1),
    ("entry level", 1),
    ("graduate", 1),
    ("alternance", 0),
    ("apprenti", 0),
    ("apprentice", 0),
    ("stagiaire", 0),
    ("stage", 0),
    ("internship", 0),
    ("intern", 0),
    ("pfe", 0),
)

QUALIFICATION_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("doctorat", 5),
    ("phd", 5),
    ("architecte", 5),
    ("architect", 5),
    ("expert", 5),
    ("ingenieur senior", 4),
    ("senior engineer", 4),
    ("ingenieur", 3),
    ("engineer", 3),
    ("bac 5", 3),
    ("bac+5", 3),
    ("master", 3),
    ("technicien superieur", 2),
    ("technicien supérieur", 2),
    ("ts", 2),
    ("bac 3", 2),
    ("bac+3", 2),
    ("licence", 2),
    ("technicien", 1),
    ("technician", 1),
    ("bac 2", 1),
    ("bac+2", 1),
    ("bts", 1),
    ("ouvrier", 0),
    ("operator", 0),
    ("operateur", 0),
    ("aide", 0),
    ("assistant", 0),
    ("assistante", 0),
)

RESPONSIBILITY_KEYWORDS: tuple[tuple[str, int], ...] = (
    ("chief technology officer", 5),
    ("directeur", 5),
    ("director", 5),
    ("head of", 5),
    ("manager", 4),
    ("responsable", 4),
    ("lead", 4),
    ("superviseur", 3),
    ("supervisor", 3),
    ("chef d equipe", 3),
    ("chef dequipe", 3),
    ("chef de section", 3),
    ("coordinateur", 3),
    ("coordinator", 3),
    ("consultant", 2),
    ("specialiste", 2),
    ("specialist", 2),
    ("developpeur", 2),
    ("developer", 2),
    ("analyste", 2),
    ("analyst", 2),
    ("assistant", 1),
    ("assistante", 1),
    ("aide", 1),
    ("stagiaire", 0),
    ("intern", 0),
    ("pfe", 0),
)

EXPERIENCE_LEVEL_TO_SENIORITY = {
    "DEBUTANT": 1,
    "JUNIOR": 1,
    "CONFIRME": 2,
    "SENIOR": 3,
}


def normalize_hierarchy_text(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("+", " + ")
    normalized = re.sub(r"[^a-z0-9\s+-]", " ", normalized)
    normalized = re.sub(r"\bbac\s*\+\s*(\d)\b", r"bac+\1", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _clean_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif value:
        raw_items = [value]
    else:
        raw_items = []
    return [str(item).strip() for item in raw_items if str(item or "").strip()]


def _get_value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _llm_enrichment(opportunity: Any) -> dict[str, Any]:
    extra_data = _get_value(opportunity, "extra_data", {}) or {}
    if not isinstance(extra_data, dict):
        return {}
    enrichment = extra_data.get("llm_enrichment") or {}
    return enrichment if isinstance(enrichment, dict) else {}


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalize_hierarchy_text(phrase)
    if not normalized_phrase:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", text) is not None


def _extract_level(text: str, keywords: tuple[tuple[str, int], ...]) -> tuple[int, tuple[str, ...]]:
    matches: list[tuple[str, int]] = []
    for keyword, level in sorted(keywords, key=lambda item: len(item[0]), reverse=True):
        if _contains_phrase(text, keyword):
            matches.append((normalize_hierarchy_text(keyword), level))
    if not matches:
        return DEFAULT_LEVEL, ()
    level = max(item[1] for item in matches)
    terms = tuple(dict.fromkeys(term for term, item_level in matches if item_level == level))
    return level, terms


def _years_to_seniority(years: Any) -> int | None:
    try:
        value = float(years)
    except (TypeError, ValueError):
        return None
    if value < 1:
        return 0
    if value < 3:
        return 1
    if value < 5:
        return 2
    return 3


def extract_hierarchy_signal(
    text: Any,
    *,
    experience_level: Any = None,
    years: Any = None,
    education_level: Any = None,
) -> HierarchySignal:
    searchable = " ".join(
        part
        for part in [
            normalize_hierarchy_text(text),
            normalize_hierarchy_text(education_level),
            normalize_hierarchy_text(experience_level),
        ]
        if part
    )
    seniority, seniority_terms = _extract_level(searchable, SENIORITY_KEYWORDS)
    qualification, qualification_terms = _extract_level(searchable, QUALIFICATION_KEYWORDS)
    responsibility, responsibility_terms = _extract_level(searchable, RESPONSIBILITY_KEYWORDS)
    seniority_detected = bool(seniority_terms)

    explicit_level = str(experience_level or "").strip().upper()
    if explicit_level in EXPERIENCE_LEVEL_TO_SENIORITY:
        seniority = (
            max(seniority, EXPERIENCE_LEVEL_TO_SENIORITY[explicit_level])
            if seniority_detected
            else EXPERIENCE_LEVEL_TO_SENIORITY[explicit_level]
        )
        if not seniority_terms:
            seniority_terms = (explicit_level.lower(),)
        seniority_detected = True

    years_level = _years_to_seniority(years)
    if years_level is not None:
        seniority = max(seniority, years_level) if seniority_detected else years_level
        if not seniority_terms:
            seniority_terms = (f"{years} years",)
        seniority_detected = True

    return HierarchySignal(
        seniority=min(MAX_LEVEL, seniority),
        qualification=min(MAX_LEVEL, qualification),
        responsibility=min(MAX_LEVEL, responsibility),
        seniority_terms=seniority_terms,
        qualification_terms=qualification_terms,
        responsibility_terms=responsibility_terms,
    )


def build_profile_hierarchy_signal(features: dict[str, Any] | None) -> HierarchySignal:
    features = features if isinstance(features, dict) else {}
    text_parts: list[str] = []
    for key in ("target_roles", "roles", "skills", "profile_skills"):
        text_parts.extend(_clean_list(features.get(key)))
    text_parts.extend(
        _clean_list(
            [
                features.get("resume_text"),
                features.get("profile_text"),
                features.get("education_level"),
            ]
        )
    )
    return extract_hierarchy_signal(
        " ".join(text_parts),
        experience_level=features.get("experience_level"),
        years=features.get("experience_years"),
        education_level=features.get("education_level"),
    )


def build_opportunity_hierarchy_signal(opportunity: Any) -> HierarchySignal:
    enrichment = _llm_enrichment(opportunity)
    text_parts: list[str] = [
        _get_value(opportunity, "titre", ""),
        _get_value(opportunity, "description", ""),
        _get_value(opportunity, "education_level", ""),
    ]
    for field in (
        "canonical_role",
        "seniority",
        "experience_level",
        "requirements",
        "responsibilities",
        "skills",
    ):
        text_parts.extend(_clean_list(enrichment.get(field)))
    text_parts.extend(_clean_list(_get_value(opportunity, "skills", [])))
    years = _get_value(opportunity, "experience_min")
    if years is None:
        years = _get_value(opportunity, "experience_years")
    return extract_hierarchy_signal(
        " ".join(str(part or "") for part in text_parts),
        experience_level=_get_value(opportunity, "experience_level")
        or enrichment.get("experience_level")
        or enrichment.get("seniority"),
        years=years,
        education_level=_get_value(opportunity, "education_level"),
    )


def validate_hierarchy_match(
    profile_signal: HierarchySignal,
    opportunity_signal: HierarchySignal,
) -> HierarchyValidation:
    seniority_gap = opportunity_signal.seniority - profile_signal.seniority
    qualification_gap = opportunity_signal.qualification - profile_signal.qualification
    responsibility_gap = opportunity_signal.responsibility - profile_signal.responsibility
    seniority_known = bool(opportunity_signal.seniority_terms)
    qualification_known = bool(opportunity_signal.qualification_terms)
    responsibility_known = bool(opportunity_signal.responsibility_terms)

    penalty = 1.0
    if seniority_known and seniority_gap > 0:
        penalty *= max(0.35, 1.0 - (0.18 * seniority_gap))
    if qualification_known and (qualification_gap >= 2 or (qualification_gap == 1 and seniority_gap >= 1)):
        penalty *= max(0.35, 1.0 - (0.22 * qualification_gap))
    if responsibility_known and responsibility_gap > 1:
        penalty *= max(0.45, 1.0 - (0.16 * (responsibility_gap - 1)))

    hierarchy_issue = "none"
    reason = "Hierarchy compatible"
    strongest_gap = max(seniority_gap, qualification_gap, responsibility_gap)
    engineer_to_technician_review = (
        profile_signal.qualification >= 3
        and opportunity_signal.qualification <= 2
        and any("technicien" in term or "technician" in term for term in opportunity_signal.qualification_terms)
    )
    if engineer_to_technician_review:
        hierarchy_issue = "overqualified_scope"
        reason = "Profile appears above the opportunity qualification scope"
        penalty *= 0.92
    elif qualification_known and qualification_gap >= 2:
        hierarchy_issue = "qualification_gap"
        reason = "Opportunity appears to require a higher qualification level"
    elif seniority_known and seniority_gap >= 2:
        hierarchy_issue = "seniority_gap"
        reason = "Seniority appears above the user's current level"
    elif responsibility_known and responsibility_gap >= 3:
        hierarchy_issue = "responsibility_gap"
        reason = "Opportunity appears to require higher responsibility scope"
    elif strongest_gap == 1:
        reason = "Slight hierarchy gap; keep as reviewable"
    elif strongest_gap == 2:
        reason = "Ambiguous hierarchy gap; LLM validation recommended"

    needs_llm = (
        hierarchy_issue == "none"
        and (
            (seniority_known and seniority_gap in {1, 2})
            or (responsibility_known and responsibility_gap in {1, 2})
            or (qualification_known and qualification_gap >= 2)
            or (qualification_known and seniority_known and qualification_gap == 1 and seniority_gap >= 1)
        )
    )
    if needs_llm:
        penalty = 1.0
    return HierarchyValidation(
        method="rules",
        score_multiplier=round(max(0.15, min(1.0, penalty)), 6),
        hierarchy_issue=hierarchy_issue,
        reason=reason,
        needs_llm=needs_llm,
        seniority_gap=seniority_gap,
        qualification_gap=qualification_gap,
        responsibility_gap=responsibility_gap,
        profile_signal=profile_signal,
        opportunity_signal=opportunity_signal,
    )
