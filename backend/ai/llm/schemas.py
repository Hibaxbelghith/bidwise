from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai.business_families import CONTROLLED_FAMILIES


MAX_LIST_ITEMS = 20
MAX_LABEL_CHARS = 80
ALLOWED_EXPERIENCE_LEVELS = {"DEBUTANT", "JUNIOR", "CONFIRME", "SENIOR"}
ALLOWED_FAMILIES = set(CONTROLLED_FAMILIES)


LLM_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_roles": {
            "type": "array",
            "items": {"type": "string", "maxLength": 60},
            "maxItems": 5,
        },
        "canonical_role": {"type": "string", "maxLength": 80},
        "skills": {
            "type": "array",
            "items": {"type": "string", "maxLength": 50},
            "maxItems": 10,
        },
        "tools": {
            "type": "array",
            "items": {"type": "string", "maxLength": 50},
            "maxItems": 8,
        },
        "soft_skills": {
            "type": "array",
            "items": {"type": "string", "maxLength": 50},
            "maxItems": 8,
        },
        "domains": {
            "type": "array",
            "items": {"type": "string", "maxLength": 60},
            "maxItems": 5,
        },
        "business_families": {
            "type": "array",
            "items": {"type": "string", "maxLength": 40},
            "maxItems": 3,
        },
        "family_confidence": {"type": "number"},
        "seniority": {"type": "string", "maxLength": 40},
        "experience_level": {"type": "string", "maxLength": 20},
        "years_experience": {"type": "integer"},
        "years_experience_min": {"type": "integer"},
        "years_experience_max": {"type": "integer"},
        "languages": {
            "type": "array",
            "items": {"type": "string", "maxLength": 30},
            "maxItems": 5,
        },
        "contract_types": {
            "type": "array",
            "items": {"type": "string", "maxLength": 30},
            "maxItems": 4,
        },
        "work_modes": {
            "type": "array",
            "items": {"type": "string", "maxLength": 30},
            "maxItems": 4,
        },
        "locations": {
            "type": "array",
            "items": {"type": "string", "maxLength": 40},
            "maxItems": 4,
        },
        "salary": {"type": "string", "maxLength": 80},
        "education_level": {"type": "string", "maxLength": 80},
        "responsibilities": {
            "type": "array",
            "items": {"type": "string", "maxLength": 180},
            "maxItems": 6,
        },
        "requirements": {
            "type": "array",
            "items": {"type": "string", "maxLength": 180},
            "maxItems": 6,
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string", "maxLength": 160},
            "maxItems": 4,
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string", "maxLength": 80},
            "maxItems": 4,
        },
        "confidence": {"type": "number"},
    },
    "required": [
        "target_roles",
        "canonical_role",
        "skills",
        "tools",
        "soft_skills",
        "domains",
        "business_families",
        "family_confidence",
        "seniority",
        "experience_level",
        "years_experience",
        "years_experience_min",
        "years_experience_max",
        "languages",
        "contract_types",
        "work_modes",
        "locations",
        "salary",
        "education_level",
        "responsibilities",
        "requirements",
        "evidence",
        "warnings",
        "confidence",
    ],
}


@dataclass(frozen=True)
class LLMExtractionResult:
    target_roles: list[str] = field(default_factory=list)
    canonical_role: str = ""
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    business_families: list[str] = field(default_factory=list)
    family_confidence: float = 0.0
    seniority: str = ""
    experience_level: str = ""
    years_experience: int | None = None
    years_experience_min: int | None = None
    years_experience_max: int | None = None
    languages: list[str] = field(default_factory=list)
    contract_types: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    salary: str = ""
    education_level: str = ""
    responsibilities: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float = 0.0
    provider: str = ""
    model: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_roles": self.target_roles,
            "canonical_role": self.canonical_role,
            "skills": self.skills,
            "tools": self.tools,
            "soft_skills": self.soft_skills,
            "domains": self.domains,
            "business_families": self.business_families,
            "family_confidence": round(float(self.family_confidence or 0.0), 4),
            "seniority": self.seniority,
            "experience_level": self.experience_level,
            "years_experience": self.years_experience,
            "years_experience_min": self.years_experience_min,
            "years_experience_max": self.years_experience_max,
            "languages": self.languages,
            "contract_types": self.contract_types,
            "work_modes": self.work_modes,
            "locations": self.locations,
            "salary": self.salary,
            "education_level": self.education_level,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "evidence": self.evidence,
            "warnings": self.warnings,
            "confidence": round(float(self.confidence or 0.0), 4),
            "provider": self.provider,
            "model": self.model,
        }


def _clean_label(value: Any, *, max_chars: int = MAX_LABEL_CHARS) -> str:
    text = str(value or "").strip()
    text = " ".join(text.split())
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text


def _clean_list(values: Any, *, max_items: int = MAX_LIST_ITEMS, max_chars: int = MAX_LABEL_CHARS) -> list[str]:
    if not isinstance(values, list):
        return []
    seen = set()
    output = []
    for value in values:
        label = _clean_label(value, max_chars=max_chars)
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        output.append(label)
        if len(output) >= max_items:
            break
    return output


def _clean_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 0 or number > 50:
        return None
    return number


def _clean_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(confidence, 1.0))


def _clean_experience_level(value: Any) -> str:
    text = _clean_label(value, max_chars=20).upper()
    aliases = {
        "ENTRY": "DEBUTANT",
        "ENTRY_LEVEL": "DEBUTANT",
        "ENTRY LEVEL": "DEBUTANT",
        "BEGINNER": "DEBUTANT",
        "DEBUTANT": "DEBUTANT",
        "DÉBUTANT": "DEBUTANT",
        "INTERNSHIP": "DEBUTANT",
        "STAGE": "DEBUTANT",
        "INTERN": "DEBUTANT",
        "JUNIOR": "JUNIOR",
        "MID": "CONFIRME",
        "MID_LEVEL": "CONFIRME",
        "MID LEVEL": "CONFIRME",
        "CONFIRME": "CONFIRME",
        "CONFIRMÉ": "CONFIRME",
        "EXPERIENCED": "CONFIRME",
        "SENIOR": "SENIOR",
        "LEAD": "SENIOR",
    }
    normalized = aliases.get(text, text)
    return normalized if normalized in ALLOWED_EXPERIENCE_LEVELS else ""


def _dedupe_skills_against_soft_skills(skills: list[str], soft_skills: list[str]) -> list[str]:
    soft_keys = {_clean_label(value).casefold() for value in soft_skills}
    return [skill for skill in skills if _clean_label(skill).casefold() not in soft_keys]


def validate_llm_extraction(
    payload: Any,
    *,
    provider: str = "",
    model: str = "",
) -> LLMExtractionResult:
    if not isinstance(payload, dict):
        payload = {}

    families = [
        family
        for family in _clean_list(payload.get("business_families"), max_items=4)
        if family in ALLOWED_FAMILIES
    ]

    years_min = _clean_int(payload.get("years_experience_min"))
    years_max = _clean_int(payload.get("years_experience_max"))
    if years_min is not None and years_max is not None and years_min > years_max:
        years_min, years_max = years_max, years_min
    years_experience = _clean_int(payload.get("years_experience"))
    if years_experience is None:
        years_experience = years_min
    if years_min is None and years_experience is not None:
        years_min = years_experience
    if years_max is None and years_experience is not None:
        years_max = years_experience

    soft_skills = _clean_list(payload.get("soft_skills"), max_items=8)
    skills = _dedupe_skills_against_soft_skills(_clean_list(payload.get("skills")), soft_skills)

    return LLMExtractionResult(
        target_roles=_clean_list(payload.get("target_roles"), max_items=8),
        canonical_role=_clean_label(payload.get("canonical_role"), max_chars=80),
        skills=skills,
        tools=_clean_list(payload.get("tools")),
        soft_skills=soft_skills,
        domains=_clean_list(payload.get("domains"), max_items=8),
        business_families=families,
        family_confidence=_clean_confidence(payload.get("family_confidence")),
        seniority=_clean_label(payload.get("seniority"), max_chars=40),
        experience_level=_clean_experience_level(payload.get("experience_level") or payload.get("seniority")),
        years_experience=years_experience,
        years_experience_min=years_min,
        years_experience_max=years_max,
        languages=_clean_list(payload.get("languages"), max_items=8),
        contract_types=_clean_list(payload.get("contract_types"), max_items=6),
        work_modes=_clean_list(payload.get("work_modes"), max_items=6),
        locations=_clean_list(payload.get("locations"), max_items=6),
        salary=_clean_label(payload.get("salary"), max_chars=80),
        education_level=_clean_label(payload.get("education_level"), max_chars=80),
        responsibilities=_clean_list(payload.get("responsibilities"), max_items=8, max_chars=180),
        requirements=_clean_list(payload.get("requirements"), max_items=8, max_chars=180),
        evidence=_clean_list(payload.get("evidence"), max_items=8, max_chars=160),
        warnings=_clean_list(payload.get("warnings"), max_items=8),
        confidence=_clean_confidence(payload.get("confidence")),
        provider=provider,
        model=model,
    )
