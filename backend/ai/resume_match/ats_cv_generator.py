from __future__ import annotations

import logging
from typing import Any

from ai.llm.providers import (
    LLMProvider,
    LLMProviderError,
    LLMProviderUnavailable,
    LLMTransientProviderError,
    get_llm_provider,
)


logger = logging.getLogger(__name__)


ATS_CV_DOCUMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "candidate_name": {"type": "string"},
        "contact_line": {"type": "string"},
        "target_title": {"type": "string"},
        "professional_summary": {"type": "string"},
        "skills_sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "items"],
                "additionalProperties": False,
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "dates": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "company", "location", "dates", "bullets"],
                "additionalProperties": False,
            },
        },
        "education": {"type": "array", "items": {"type": "string"}},
        "tools": {"type": "array", "items": {"type": "string"}},
        "languages": {"type": "array", "items": {"type": "string"}},
        "verification_notes": {"type": "array", "items": {"type": "string"}},
        "keywords_added": {"type": "array", "items": {"type": "string"}},
        "keywords_missing": {"type": "array", "items": {"type": "string"}},
        "ats_score_10": {"type": "number"},
        "matching_percent": {"type": "number"},
    },
    "required": [
        "candidate_name",
        "contact_line",
        "target_title",
        "professional_summary",
        "skills_sections",
        "experience",
        "education",
        "tools",
        "languages",
        "verification_notes",
        "keywords_added",
        "keywords_missing",
        "ats_score_10",
        "matching_percent",
    ],
    "additionalProperties": False,
}


class ATSResumeGenerationError(RuntimeError):
    """Raised when the ATS CV generator cannot produce safe structured content."""


def generate_ats_cv_document(
    evidence: dict[str, Any],
    *,
    optimization_markdown: str = "",
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        raise ATSResumeGenerationError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ATSResumeGenerationError("Resume match evidence is not ready for ATS CV export.")

    llm_provider = provider or get_llm_provider()
    prompt = build_ats_cv_document_prompt(evidence, optimization_markdown=optimization_markdown)

    try:
        payload = llm_provider.generate_json(prompt, schema=ATS_CV_DOCUMENT_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "ATS CV document LLM failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        raise ATSResumeGenerationError(str(exc)) from exc

    document = _normalize_document_payload(payload, evidence)
    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(llm_provider, "provider_name", ""),
        "model": getattr(llm_provider, "model", ""),
        "document": document,
    }


def build_ats_cv_document_prompt(evidence: dict[str, Any], *, optimization_markdown: str = "") -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    contact = _dict(profile.get("contact"))

    return f"""
You are BidWise AI, a senior recruiter, ATS resume writer, and professional CV editor.

TASK:
Generate structured content for one clean ATS-friendly resume DOCX tailored to the job offer.
The backend will apply the Word template. You only generate content.

ABSOLUTE RULES:
- Use only the evidence below.
- Never invent employers, dates, diplomas, certifications, projects, tools, or achievements.
- If a fact is not proven, do not include it in the resume body.
- Put uncertain items only in verification_notes.
- Do not write in first person.
- Do not write in third person.
- Do not start the professional summary with the candidate name.
- Use the same language as the job offer. Do not mix languages.
- Keep the target_title short, not a keyword list.
- Keep the resume concise: maximum 4 skill groups and maximum 6 experience bullets per job.
- Return only valid JSON matching the schema.

DOMAIN ADAPTATION:
- Accounting/finance: prioritize bookkeeping, bank reconciliation, client/supplier accounts,
  tax declarations, VAT/TVA, closing support, Excel, accounting software, compliance, archiving.
- IT: prioritize technologies, frameworks, APIs, projects, GitHub, testing, deployment.
- Marketing: prioritize campaigns, KPIs, SEO, social media, analytics tools.
- HR/admin: prioritize recruitment, onboarding, administration, communication, documentation.
- Sales: prioritize CRM, prospecting, negotiation, sales targets, client follow-up.

FINAL RESUME SECTIONS TO GENERATE:
- candidate_name
- contact_line
- target_title
- professional_summary
- skills_sections
- experience
- education
- tools
- languages

INTERNAL METADATA:
- verification_notes: items the candidate should verify, not part of the final CV body.
- keywords_added and keywords_missing: short ATS tracking lists.
- ats_score_10 and matching_percent: the backend will verify these values.

==================================================
CANDIDATE DATA
==================================================
Name: {_text(contact.get("full_name"))}
Email: {_text(contact.get("email"))}
Preferred locations: {_list(profile.get("locations"))}
Target roles: {_list(profile.get("target_roles"))}
Profile level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Profile-declared skills are context only, not proof: {_list(profile.get("skills"))}

Resume role: {_text(resume.get("canonical_role"))}
Resume skills: {_list(resume.get("skills"))}
Resume tools: {_list(resume.get("tools"))}
Resume domains: {_list(resume.get("domains"))}
Resume excerpt: {_text(resume.get("summary_excerpt"))}

==================================================
JOB OPPORTUNITY DATA
==================================================
Title: {_text(opportunity.get("title"))}
Company: {_text(opportunity.get("company"))}
Location: {_text(opportunity.get("location"))}
Contract: {_text(opportunity.get("contract"))}
Experience required: {_nested(opportunity, "experience", "min")} - {_nested(opportunity, "experience", "max")} years
Education: {_text(opportunity.get("education"))}
Required skills: {_list(opportunity.get("skills"))}
Responsibilities: {_list(opportunity.get("responsibilities"))}
Requirements: {_list(opportunity.get("requirements"))}
Description excerpt: {_text(opportunity.get("description_excerpt"))}

==================================================
ATS SIGNALS
==================================================
BidWise fit score: {_text(match.get("fit_score"))}%
ATS keyword coverage: {_text(ats.get("keyword_coverage_percent"))}%
Keywords already present: {_list(ats.get("covered_keywords"))}
Missing or weak keywords: {_list(ats.get("missing_or_weak_keywords"))}
Critical gaps: {_list(prioritized_gaps.get("critical"))}
Useful gaps: {_list(prioritized_gaps.get("useful"))}

==================================================
OPTIMIZATION CONTEXT
==================================================
Use this only as guidance. Do not copy internal notes into the final resume body.
{str(optimization_markdown or "")[:3500]}
""".strip()


def _normalize_document_payload(payload: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ATSResumeGenerationError("ATS CV payload must be a dictionary.")

    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    contact = _dict(profile.get("contact"))

    candidate_name = _clean_text(payload.get("candidate_name")) or _clean_text(contact.get("full_name")) or "[Candidate Name]"
    email = _clean_text(contact.get("email")) or "[Email]"
    location = _first(_list_raw(profile.get("locations"))) or "[City]"
    contact_line = _clean_text(payload.get("contact_line")) or f"{location} | {email} | [Phone]"

    target_title = _clean_text(payload.get("target_title")) or _first(_list_raw(profile.get("target_roles"))) or _clean_text(resume.get("canonical_role")) or "Professional Profile"
    summary = _clean_text(payload.get("professional_summary"))
    if not summary:
        raise ATSResumeGenerationError("ATS CV payload is missing professional_summary.")

    document = {
        "candidate_name": candidate_name,
        "contact_line": contact_line,
        "target_title": _limit_words(target_title, 8),
        "professional_summary": summary,
        "skills_sections": _normalize_skill_sections(payload.get("skills_sections")),
        "experience": _normalize_experience(payload.get("experience")),
        "education": _list_clean(payload.get("education"))[:4],
        "tools": _list_clean(payload.get("tools"))[:10],
        "languages": _list_clean(payload.get("languages"))[:6],
        "verification_notes": _list_clean(payload.get("verification_notes"))[:6],
        "keywords_added": _list_clean(payload.get("keywords_added"))[:10],
        "keywords_missing": _list_clean(payload.get("keywords_missing"))[:10],
        "ats_score_10": _ats_score_10(ats.get("keyword_coverage_percent")),
        "matching_percent": _score_percent(match.get("fit_score")),
    }

    if not document["skills_sections"]:
        raise ATSResumeGenerationError("ATS CV payload is missing skills_sections.")
    return document


def _normalize_skill_sections(value: Any) -> list[dict[str, Any]]:
    sections = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        items = _list_clean(item.get("items"))[:8]
        if title and items:
            sections.append({"title": title, "items": items})
    return sections[:4]


def _normalize_experience(value: Any) -> list[dict[str, Any]]:
    entries = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        bullets = _list_clean(item.get("bullets"))[:6]
        title = _clean_text(item.get("title"))
        if not title or not bullets:
            continue
        entries.append(
            {
                "title": title,
                "company": _clean_text(item.get("company")),
                "location": _clean_text(item.get("location")),
                "dates": _clean_text(item.get("dates")),
                "bullets": bullets,
            }
        )
    return entries[:4]


def _ats_score_10(value: Any) -> float:
    try:
        return round(max(0.0, min(100.0, float(value))) / 10.0, 1)
    except (TypeError, ValueError):
        return 0.0


def _score_percent(value: Any) -> float:
    try:
        return round(max(0.0, min(100.0, float(value))), 1)
    except (TypeError, ValueError):
        return 0.0


def _limit_words(value: str, max_words: int) -> str:
    words = str(value or "").split()
    return " ".join(words[:max_words]) if len(words) > max_words else str(value or "")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    if value in (None, ""):
        return "not visible"
    text = str(value).strip()
    return text or "not visible"


def _list(value: Any) -> str:
    items = _list_raw(value)
    return ", ".join(items) if items else "not visible"


def _list_raw(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        raw = [value]
    elif isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = [value]
    return [str(item).strip() for item in raw if str(item or "").strip()]


def _list_clean(value: Any) -> list[str]:
    return [_clean_text(item) for item in _list_raw(value) if _clean_text(item)]


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"not visible", "not visible in resume", "none", "null"}:
        return ""
    return " ".join(text.split())


def _nested(value: dict[str, Any], *keys: str) -> str:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return "not visible"
        current = current.get(key)
    return _text(current)


def _first(values: list[str]) -> str:
    return values[0] if values else ""
