from __future__ import annotations

import re
from typing import Any

from django.conf import settings

from ai.business_families import PRIMARY_BUSINESS_FAMILIES, PRIMARY_BUSINESS_FAMILY_DESCRIPTIONS
from ai.llm.providers import LLMProvider, OllamaProvider, get_llm_provider
from ai.llm.schemas import LLMExtractionResult, validate_llm_extraction

from .models import ResumeSemanticSignals, SkillCandidate
from .normalization import clean_resume_semantic_text


MAX_STRUCTURED_RESUME_INPUT_CHARS = 2500
STRUCTURED_RESUME_VERSION = "qwen-structured-resume-v1"

RESUME_OFFICIAL_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "target_roles": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "canonical_role": {"type": "string"},
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Cross-cutting verifiable abilities such as leadership, budgeting, "
                "project management, negotiation or technical writing. Never duplicate tools."
            ),
            "maxItems": 12,
        },
        "tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Verbatim named resources from the CV: software, programming languages, "
                "frameworks, databases, instruments, certifications, platforms, "
                "methodologies and standards. No paraphrase, no grouping."
            ),
            "maxItems": 10,
        },
        "domains": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "business_families": {
            "type": "array",
            "items": {"type": "string", "enum": list(PRIMARY_BUSINESS_FAMILIES)},
            "maxItems": 2,
        },
        "family_confidence": {"type": "number"},
        "experience_level": {"type": "string"},
        "years_experience": {"type": ["integer", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "contract_types": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "locations": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "confidence": {"type": "number"},
    },
    "required": [
        "target_roles",
        "canonical_role",
        "skills",
        "tools",
        "domains",
        "business_families",
        "family_confidence",
        "experience_level",
        "years_experience",
        "languages",
        "contract_types",
        "locations",
        "confidence",
    ],
}

class StructuredResumeExtractionError(RuntimeError):
    pass


PROFILE_BUSINESS_FAMILIES = "\n".join(
    f"- {family}: {PRIMARY_BUSINESS_FAMILY_DESCRIPTIONS[family]}"
    for family in PRIMARY_BUSINESS_FAMILIES
)

CONTROLLED_FAMILY_IDS = set(PRIMARY_BUSINESS_FAMILIES)

def build_resume_extraction_prompt(text: str) -> str:
    return f"""
Extract CV signals for job matching. Return JSON only.
Use only explicit CV evidence. Do not invent.
Allowed business_families ids:
{PROFILE_BUSINESS_FAMILIES}
Rules:
- canonical_role and target_roles: job titles only, never business_families ids. Prefer the CV headline/title when present.
- business_families: exact ids only, never display labels. Use one primary family by default; use two only when the CV clearly contains two distinct professional tracks.
- family_confidence: confidence in the selected business_families, from 0 to 1.
- domains: free-text professional domains from the CV, not family ids.
- tools: copy VERBATIM every named resource from the CV, regardless of domain:
  software, programming languages, frameworks, databases, machines, instruments,
  certifications, standards, ERP/CRM/BI platforms, methodologies, protocols,
  regulations. Never paraphrase ("bases de données SQL" is wrong; "PostgreSQL"
  is right). Never group ("outils Microsoft" is wrong; "Excel", "Word",
  "Teams" is right).
- skills: verifiable cross-cutting abilities only (leadership, negotiation,
  project management, technical writing, budgeting...). Never repeat something
  already in tools.
- skills/tools labels: short, human-readable, no snake_case/raw ids.
- contract_types: split combined values, e.g. "CDI / CDD" -> ["CDI", "CDD"].
- years_experience: for ranges such as "3-5 years", use the lower bound.
- experience_level: DEBUTANT 0-1, JUNIOR 1-2, CONFIRME 3-5, SENIOR 6+.
- languages only when explicitly listed.
- locations are cities/regions only, not countries.
- unknown fields: [] / "" / null.
CV:
{text}
""".strip()


COUNTRY_LOCATION_LABELS = {"tunisie", "tunisia"}


def _clean_list(values: Any, *, limit: int = 20) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    output: list[str] = []
    seen = set()
    for value in values:
        text = " ".join(str(value or "").strip().split())
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _clean_human_label(value: Any) -> str:
    text = str(value or "").strip()
    text = " ".join(text.split())
    return text


def _compact_label(value: str) -> str:
    return re.sub(r"[\W_]+", "", str(value or ""), flags=re.UNICODE).casefold()


def _source_surface_forms(text: str) -> dict[str, str]:
    forms: dict[str, str] = {}
    for match in re.finditer(r"[\w.+#/-]+", text or "", flags=re.UNICODE):
        label = match.group(0).strip(".,;:()[]{}")
        compact = _compact_label(label)
        if len(compact) < 3 or compact in forms:
            continue
        forms[compact] = label
    return forms


def _restore_source_surface(label: str, surface_forms: dict[str, str] | None = None) -> str:
    if not surface_forms:
        return label
    return surface_forms.get(_compact_label(label), label)


def _expand_resume_label(value: Any) -> list[str]:
    text = _clean_human_label(value)
    if not text:
        return []
    if "," not in text and "/" not in text:
        return [text]
    return [_clean_human_label(part) for part in re.split(r"[,/]+", text) if _clean_human_label(part)]


def _label_words(value: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[\w]+", value.casefold(), flags=re.UNICODE)
        if len(word) > 2
    }


def _clean_resume_labels(
    values: Any,
    *,
    limit: int = 20,
    surface_forms: dict[str, str] | None = None,
) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    output: list[str] = []
    seen = set()
    for value in values:
        for label in _expand_resume_label(value):
            label = _restore_source_surface(label, surface_forms)
            key = label.casefold()
            if not label or key in seen:
                continue
            words = _label_words(label)
            if words and any(words > _label_words(existing) for existing in output):
                continue
            seen.add(key)
            output.append(label)
            if len(output) >= limit:
                return output
    return output


def _clean_locations(values: Any, *, limit: int = 6) -> list[str]:
    output: list[str] = []
    seen = set()
    for value in _clean_list(values, limit=20):
        parts = [part.strip() for part in value.replace("/", ",").split(",")]
        for part in parts:
            label = _clean_human_label(part)
            key = label.casefold()
            if not label or key in COUNTRY_LOCATION_LABELS or key in seen:
                continue
            seen.add(key)
            output.append(label)
            if len(output) >= limit:
                return output
    return output


def _clean_split_labels(values: Any, *, limit: int = 8) -> list[str]:
    output: list[str] = []
    seen = set()
    for value in _clean_list(values, limit=20):
        for part in re.split(r"[,/]+", value):
            label = " ".join(str(part or "").strip().split())
            key = label.casefold()
            if not label or key in seen:
                continue
            seen.add(key)
            output.append(label)
            if len(output) >= limit:
                return output
    return output


def _candidate_records(
    result: LLMExtractionResult,
    *,
    surface_forms: dict[str, str] | None = None,
) -> list[SkillCandidate]:
    candidates: list[SkillCandidate] = []
    for label in _clean_resume_labels([*result.skills, *result.tools], limit=40, surface_forms=surface_forms):
        candidates.append(
            SkillCandidate(
                text=label,
                source="qwen_structured",
                confidence=max(0.0, min(float(result.confidence or 0.0), 1.0)),
            )
        )
    return candidates


def _profile_suggestions(
    result: LLMExtractionResult,
    *,
    business_families: list[str],
    experience_level: str,
    domains: list[str],
    surface_forms: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "target_roles": _clean_target_roles(result),
        "competences": _clean_resume_labels([*result.skills, *result.tools], limit=30, surface_forms=surface_forms),
        "domaines_interet": business_families,
        "preferred_locations": _clean_locations(result.locations),
        "employment_types": _clean_split_labels(result.contract_types, limit=6),
        "work_mode_preferences": result.work_modes,
        "niveau_experience": experience_level,
        "annees_experience": result.years_experience,
        "languages": result.languages,
    }


def _infer_experience_level(result: LLMExtractionResult) -> str:
    if result.experience_level:
        return result.experience_level
    years = result.years_experience
    if years is None:
        return ""
    if years <= 0:
        return "DEBUTANT"
    if years <= 2:
        return "JUNIOR"
    if years <= 5:
        return "CONFIRME"
    return "SENIOR"


def _clean_target_roles(result: LLMExtractionResult) -> list[str]:
    roles = [
        role
        for role in _clean_list(result.target_roles, limit=8)
        if role.casefold() not in CONTROLLED_FAMILY_IDS
    ]
    canonical_role = _clean_canonical_role(result)
    if canonical_role and canonical_role.casefold() not in {role.casefold() for role in roles}:
        roles.insert(0, canonical_role)
    return roles[:8]


def _clean_canonical_role(result: LLMExtractionResult) -> str:
    role = " ".join(str(result.canonical_role or "").split())
    return "" if role.casefold() in CONTROLLED_FAMILY_IDS else role


def _clean_domains(result: LLMExtractionResult) -> list[str]:
    return [
        domain
        for domain in _clean_list(result.domains, limit=12)
        if domain.casefold() not in CONTROLLED_FAMILY_IDS
    ]


def _rank_business_families(result: LLMExtractionResult) -> list[str]:
    families = _clean_list(
        [
            *result.business_families,
            *[
                domain
                for domain in result.domains
                if str(domain or "").casefold() in CONTROLLED_FAMILY_IDS
            ],
        ],
        limit=4,
    )
    return [family for family in families if family in CONTROLLED_FAMILY_IDS][:2]


def _resume_llm_provider(provider: LLMProvider | None = None) -> LLMProvider:
    if provider is not None:
        return provider
    configured_provider = str(getattr(settings, "LLM_PROVIDER", "") or "").strip().lower()
    if configured_provider == "ollama":
        return OllamaProvider(
            model=str(getattr(settings, "PROFILE_RESUME_QWEN_MODEL", "") or getattr(settings, "OLLAMA_MODEL", "")).strip(),
            base_url=str(getattr(settings, "OLLAMA_BASE_URL", "") or "http://host.docker.internal:11434").rstrip("/"),
            timeout_seconds=float(getattr(settings, "PROFILE_RESUME_QWEN_TIMEOUT_SECONDS", 180.0)),
            temperature=float(getattr(settings, "PROFILE_RESUME_QWEN_TEMPERATURE", 0.0)),
            max_output_tokens=int(getattr(settings, "PROFILE_RESUME_QWEN_MAX_TOKENS", 300)),
            keep_alive=str(getattr(settings, "PROFILE_RESUME_QWEN_KEEP_ALIVE", "30m") or "").strip(),
        )
    return get_llm_provider()


def extract_structured_resume_signals(
    text: str,
    *,
    provider: LLMProvider | None = None,
) -> ResumeSemanticSignals:
    cleaned = clean_resume_semantic_text(
        text,
        max_chars=int(getattr(settings, "PROFILE_RESUME_QWEN_TEXT_CHARS", MAX_STRUCTURED_RESUME_INPUT_CHARS)),
    )
    if not cleaned:
        return ResumeSemanticSignals(warnings=["empty_resume_text"])

    llm_provider = _resume_llm_provider(provider)
    try:
        payload = llm_provider.generate_json(
            build_resume_extraction_prompt(cleaned),
            schema=RESUME_OFFICIAL_EXTRACTION_SCHEMA,
        )
    except Exception as exc:  # noqa: BLE001 - caller decides whether to fallback
        raise StructuredResumeExtractionError(str(exc) or exc.__class__.__name__) from exc

    result = validate_llm_extraction(
        payload,
        provider=getattr(llm_provider, "provider_name", ""),
        model=getattr(llm_provider, "model", ""),
    )
    experience_level = _infer_experience_level(result)
    business_families = _rank_business_families(result)
    domains = _clean_domains(result)
    surface_forms = _source_surface_forms(cleaned)
    result_payload = result.as_dict()
    result_payload["experience_level"] = experience_level
    result_payload["business_families"] = business_families
    result_payload["target_roles"] = _clean_target_roles(result)
    result_payload["canonical_role"] = _clean_canonical_role(result)
    result_payload["domains"] = domains

    warnings = _clean_list(result.warnings, limit=8)
    warnings.append("structured_resume_extraction:qwen")

    return ResumeSemanticSignals(
        skills=_clean_resume_labels(result.skills, limit=20, surface_forms=surface_forms),
        domains=domains,
        tools=_clean_resume_labels(result.tools, limit=16, surface_forms=surface_forms),
        business_families=business_families,
        family_confidence=result.family_confidence,
        canonical_role=_clean_canonical_role(result),
        target_roles=_clean_target_roles(result),
        languages_detected=_clean_list(result.languages, limit=8),
        semantic_confidence=result.confidence,
        llm_enrichment={
            "version": STRUCTURED_RESUME_VERSION,
            "provider": result.provider,
            "model": result.model,
            "result": result_payload,
            "profile_suggestions": _profile_suggestions(
                result,
                business_families=business_families,
                experience_level=experience_level,
                domains=domains,
                surface_forms=surface_forms,
            ),
        },
        raw_candidates=_candidate_records(result, surface_forms=surface_forms),
        warnings=warnings,
    )
