from __future__ import annotations

import html
import re
from typing import Any

from users.resume_semantic.normalization import clean_resume_semantic_text

from .providers import LLMProvider, generate_extraction_json, get_llm_provider
from .schemas import LLMExtractionResult, validate_llm_extraction


MAX_LLM_INPUT_CHARS = 6500
MAX_CONTEXT_SECTION_CHARS = 2800

CONTROLLED_FAMILY_PROMPT = """
software_web, data_ai, it_network_support, accounting_finance_audit,
sales_business, marketing_communication, hr_administration,
quality_industry_methods, engineering_construction, legal_regulatory,
healthcare, education_training, logistics_supply_chain, design_creative,
customer_support, security_safety, other
""".strip()

LEGACY_FAMILY_PROMPT = """
backend, frontend, fullstack, data_ai, accounting_finance, marketing, sales, hr,
design, it_support_network, quality_industry, engineering_construction,
administration, education_training, legal, other
""".strip()

FAMILY_DECISION_PROMPT = """
- software_web: software products, web/mobile apps, frontend, backend, fullstack, QA automation, DevOps.
- data_ai: BI, analytics, AI, machine learning, data engineering, data science.
- it_network_support: helpdesk, user support, systems, networks, Microsoft 365, Active Directory, cybersecurity, hardware/software installation.
- accounting_finance_audit: accounting, audit, tax, payroll, banking or finance operations.
- sales_business: sales, business development, key accounts, commercial offers and negotiations.
- marketing_communication: marketing, SEO/SEA, communication, content, community management.
- hr_administration: HR, recruitment, office administration, executive assistant.
- quality_industry_methods: factory production, industrial methods, maintenance, quality, QHSE, process, foodtech, oil/gas operations.
- engineering_construction: civil engineering, construction, site works, structures, BIM, hydraulics, infrastructure, architecture/BTP.
- legal_regulatory: legal, compliance, regulatory affairs.
- healthcare: medical, paramedical, pharmacy, dental, nursing, clinical care, operating room, anesthesia, pediatrics, patient care.
- education_training: teaching, training, pedagogy, coaching.
- logistics_supply_chain: logistics, warehouse, procurement, transport, supply chain.
- design_creative: graphic design, UX/UI, multimedia, creative production.
- customer_support: call center, customer support, reception, client service.
- security_safety: physical security, guard roles, surveillance, access control, fire safety, prevention/security operations.
- other: only when no family clearly applies.
""".strip()


class LLMEnrichmentError(RuntimeError):
    pass


def _trim_text(text: str, *, max_chars: int = MAX_LLM_INPUT_CHARS) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[:max_chars].strip()


def _clean_list(values: Any, *, limit: int = 12) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    output = []
    seen = set()
    for value in values:
        text = _trim_text(str(value or ""), max_chars=120)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _source_name(opportunity: Any) -> str:
    source = getattr(opportunity, "source", None)
    return _trim_text(getattr(source, "nom", "") or getattr(opportunity, "source_name", ""), max_chars=80)


def _extra_data(opportunity: Any) -> dict[str, Any]:
    value = getattr(opportunity, "extra_data", None)
    return value if isinstance(value, dict) else {}


def _format_bullets(title: str, values: list[str]) -> str:
    if not values:
        return ""
    bullets = "\n".join(f"- {value}" for value in values)
    return f"{title}:\n{bullets}"


def _html_to_context_text(value: str, *, max_chars: int = MAX_CONTEXT_SECTION_CHARS) -> str:
    text = str(value or "")
    if not text.strip():
        return ""
    text = re.sub(r"(?i)</(li|p|div|h[1-6]|br)>", "\n", text)
    text = re.sub(r"(?i)<(li|p|div|h[1-6])[^>]*>", "\n- ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = []
    for raw_line in text.splitlines():
        line = _trim_text(raw_line, max_chars=220)
        if line:
            lines.append(line)
    return "\n".join(lines)[:max_chars].strip()


def _build_known_fields(opportunity: Any) -> str:
    extra = _extra_data(opportunity)
    skills = _clean_list(getattr(opportunity, "skills", []) or [])
    languages = _clean_list(getattr(opportunity, "languages_fallback", []) or [])
    contract_types = _clean_list(extra.get("contract_types")) or _clean_list([getattr(opportunity, "contract_type", "")])
    education_levels = _clean_list(extra.get("education_levels")) or _clean_list([getattr(opportunity, "education_level", "")])

    experience_parts = []
    experience_text = _trim_text(extra.get("experience_text") or extra.get("experience") or "", max_chars=80)
    if experience_text:
        experience_parts.append(experience_text)
    minimum = getattr(opportunity, "experience_min", None)
    maximum = getattr(opportunity, "experience_max", None)
    if minimum is not None and maximum is not None:
        experience_parts.append(f"{minimum}-{maximum} years")
    elif minimum is not None:
        experience_parts.append(f"{minimum}+ years")

    fields = [
        ("Source", _source_name(opportunity)),
        ("Location", getattr(opportunity, "ville", "")),
        ("Contract", ", ".join(contract_types)),
        ("Availability", getattr(opportunity, "availability", "")),
        ("Work mode", getattr(opportunity, "normalized_work_mode", "")),
        ("Experience", ", ".join(experience_parts)),
        ("Education", ", ".join(education_levels)),
        ("Salary", getattr(opportunity, "salary", "")),
        ("Company sector", extra.get("company_sector") or extra.get("sector") or extra.get("industry")),
        ("Existing skills", ", ".join(skills)),
        ("Known human languages", ", ".join(languages)),
    ]
    lines = [f"- {label}: {_trim_text(value, max_chars=180)}" for label, value in fields if _trim_text(value, max_chars=180)]
    return "Known structured fields:\n" + "\n".join(lines) if lines else "Known structured fields: none"


def _build_opportunity_context(opportunity: Any) -> str:
    description = _trim_text(getattr(opportunity, "description", ""), max_chars=MAX_CONTEXT_SECTION_CHARS)
    description_html = _html_to_context_text(getattr(opportunity, "description_html", ""))
    # Many job boards store the same content twice: once as plain text and
    # once as HTML/list markup. Prefer the structured list view when present;
    # it gives the LLM section boundaries without doubling CPU tokens.
    description_section = ""
    if description_html:
        description_section = "Description sections:\n" + description_html
    elif description:
        description_section = "Description text:\n" + description
    sections = [
        _build_known_fields(opportunity),
        description_section,
    ]
    return "\n\n".join(section for section in sections if section).strip()[:MAX_LLM_INPUT_CHARS]


def _resume_prompt(text: str) -> str:
    return f"""
You are an information extraction engine for BidWise, a job recommendation platform.
Extract only evidence explicitly supported by the CV text. Do not invent skills.
Return strict JSON matching the schema.

Use business_families only as a coarse optional guardrail. The most important fields are
canonical_role, target_roles, skills, tools, domains, responsibilities, and requirements.
Use only controlled business_families. Prefer the product families when possible:
{CONTROLLED_FAMILY_PROMPT}
Do not return legacy aliases for opportunities.

Rules:
- Put programming languages, frameworks, software tools, business tools, and professional skills in skills/tools.
- Ignore generic action verbs and vague phrases such as "manage", "assist", "team", "pressure".
- target_roles should be probable job roles from the CV, not all past company names.
- canonical_role should be the strongest single target role when clear.
- experience_level must be one of DEBUTANT, JUNIOR, CONFIRME, SENIOR, or "" if unknown.
- years_experience is one representative explicit number only: 0 for internship/fresh graduate, 2 for "2 years" or "2-5 years", null when unknown.
- responsibilities and requirements should summarize only professional evidence useful for matching.
- Return compact lists only: at most 5 roles, 10 skills, 8 tools, 5 domains, 4 evidence items.
- Prefer canonical short labels such as "Python", "Django", "Accounting", "Excel".
- confidence is 0..1 based on clarity of evidence.
- evidence must be short phrases from the CV without private contact data.
- Do not expand acronyms unless the expansion is explicitly present in the text.
- family_confidence is 0..1. Use <=0.5 when the controlled family is uncertain.
- If the family is uncertain, set business_families to ["other"] and rely on domains/skills.
- Put human languages only in languages, never in skills or tools.

CV text:
{text}
""".strip()


def _opportunity_prompt(
    *,
    title: str,
    context: str,
    company: str = "",
    source: str = "",
) -> str:
    return f"""
You are an information extraction engine for BidWise, a job recommendation platform.
Extract structured recommendation signals from this scraped job opportunity.
Return strict JSON matching the schema.

Use business_families only as a coarse optional guardrail. The most important fields are
canonical_role, target_roles, skills, tools, domains, responsibilities, and requirements.
Use only controlled business_families. Prefer the product families when possible:
{CONTROLLED_FAMILY_PROMPT}
Do not return legacy aliases for opportunities.

Rules:
- The input may come from Keejob, EmploiTunisie, LinkedIn, or public tender sources with different field coverage.
- Use Known structured fields first when present, then complete missing fields from description/list context.
- For Keejob, structured fields such as Location, Contract, Experience, Education, Company sector, Existing skills, and Known human languages are usually reliable; copy them into the appropriate JSON fields instead of rediscovering them.
- For Keejob descriptions, section headers like "Les attributions", "Missions", "Votre profil", "Profil recherché", "Qualités", and "Les spécificités du poste" usually contain the strongest matching evidence.
- Extract real skills/tools even when the existing structured skills list is empty or incomplete.
- skills are professional capabilities required to perform the job.
- tools are software, frameworks, platforms, machines, instruments, or named methods used in the job.
- soft_skills are behavioral or interpersonal qualities expected from the candidate, such as rigour, communication, teamwork, autonomy, responsibility, discretion, motivation, stress resistance, observation, and adaptability.
- languages are human spoken/written languages such as French, English, Arabic, Italian, German, or Spanish.
- Never put a human language in skills or tools; put it only in languages.
- Skills should be short reusable matching labels extracted from tasks and requirements, not full sentences.
- Skills should be technical, domain, tool, method, regulatory, clinical, commercial, or operational capabilities.
- Prefer deriving skills from mission/responsibility/action sections. Do not create skills by copying isolated candidate qualities from profile/qualities sections.
- If the only evidence for a label is a personal quality, work style, attitude, or behavior, put it in soft_skills and keep it out of skills.
- When responsibilities are visible, convert the main operational tasks into short capability labels for skills when they are useful for matching.
- Put soft traits in soft_skills, and also keep the full profile sentence in requirements when useful. Do not put soft traits in skills unless the role is specifically about that capability.
- Never duplicate the same label in skills and soft_skills. If a label describes personality, attitude, communication style, work style, or interpersonal behavior, it belongs only in soft_skills.
- Examples that belong in soft_skills only: sérieux, rigoureux, dynamique, motivé, autonomie, communication, esprit d'équipe, responsabilité, réactivité, discrétion, professionnalisme, résistance au stress, adaptabilité.
- For security_safety roles, derive skills from operational duties such as surveillance, access control, incident prevention, applying security procedures, protecting people/property, fire safety, safety rounds, or emergency response. Do not use profile qualities such as observation, discretion, rigour, or professionalism as skills.
- For healthcare roles, derive skills from clinical duties, care procedures, medical equipment, patient care, operating room practice, pharmacy stock, anesthesia/reanimation, or hygiene/safety protocols. Put personality traits only in soft_skills.
- If a task says "contrôler la qualité", add a short skill such as "Contrôle qualité".
- If a task says "planifier la production", add a short skill such as "Planification de production".
- If a task says "assurer la traçabilité" or "respecter QHSSE/ISO", add short skills such as "Traçabilité", "QHSE", or "Normes ISO" when supported by text.
- If a candidate skill is only a generic office condition and the description gives no tasks or requirements around it, keep it out of skills and explain the uncertainty in warnings.
- Do not include generic words like "quality", "management", or "team" unless they are clearly a professional domain.
- business_families is secondary. Prefer exact free-text domains over forced classification.
- Choose business_families from this taxonomy after reading the title, known structured fields, company sector, domains, tasks, and requirements:
{FAMILY_DECISION_PROMPT}
- If the structured company sector/domain clearly belongs to one family, use it to resolve ambiguous titles.
- The selected family must explain the actual work environment and responsibilities, not just a single ambiguous word in the title.
- Use engineering_construction only for construction/infrastructure/site/civil engineering work. Do not use it for generic production, factory operations, QHSE, maintenance, oil/gas filling, or agro-food production; use quality_industry_methods for those.
- Do not use engineering_construction for operating room, clinical, nursing, pharmacy, anesthesia, or patient-care roles; use healthcare for those.
- Use it_network_support for helpdesk, support IT, Microsoft 365, Active Directory, Windows systems, network devices, cybersecurity, hardware/software installation, and user account administration, even when the description mentions maintenance.
- Use fullstack/backend/frontend/data_ai only for real software/data roles, not for engineering, construction, hydraulic, architecture, or office roles.
- If no controlled family clearly fits, use ["other"] instead of guessing.
- family_confidence is 0..1. Use >=0.8 only when the controlled family is explicit and obvious.
- Use <=0.5 for uncertain family mapping; this lets ranking rely on JobBERT/domain text instead.
- Do not expand acronyms unless the expansion is explicitly present in the text. Keep acronyms as written.
- Put human languages only in languages, never in skills or tools.
- If a tool acronym is visible, return the acronym as written. Do not add a parenthetical expansion.
- target_roles should be job titles/roles, not company names.
- canonical_role should be the best normalized job role from the offer.
- experience_level must be one of DEBUTANT, JUNIOR, CONFIRME, SENIOR, or "" if unknown.
- DEBUTANT means internship, fresh graduate, beginner, entry-level, no experience, or 0-1 year.
- JUNIOR means junior profile or about 1-2 years.
- CONFIRME means confirmed, experienced, mid-level, or about 2-5 years.
- SENIOR means senior, lead, manager-level technical role, or 5+ years.
- years_experience is one representative explicit number only: 0 for internship/fresh graduate, 2 for "2 years" or "2-5 years", 5 for "minimum 5 years", null when unknown.
- contract_types and work_modes should be inferred only when visible.
- locations, salary, education_level, experience_level, and years_experience must be extracted only when explicit or strongly implied by standard wording.
- responsibilities must summarize actual tasks from mission/attribution sections, such as supervise works, plan production, control quality, coordinate teams, prepare reports, maintain equipment.
- requirements must summarize required profile conditions from profile/requirements sections, such as diploma, years of experience, domain knowledge, tools, languages, mobility, certifications.
- requirements should keep important details but avoid long copied paragraphs.
- If the description is longer than 500 characters, do not return empty responsibilities unless no tasks are visible.
- If the description contains "profil", "expérience", "diplôme", "maîtrise", "bonne connaissance", or equivalent profile wording, do not return empty requirements.
- If responsibilities or requirements are visible in the description, return them even when the structured skills list already exists.
- If you cannot extract responsibilities or requirements from a long description, lower confidence instead of returning confidence 1.0.
- Return compact lists only: at most 5 roles, 10 skills, 8 tools, 5 domains, 6 responsibilities, 6 requirements, 4 evidence items.
- Prefer canonical short labels such as "React", "Node.js", "Accounting", "Excel".
- confidence is 0..1 based on clarity of evidence.
- evidence must be short phrases from the opportunity text.

Return every field in this JSON shape. Use [] for unknown lists, "" for unknown strings, and null for unknown numbers:
{{
  "target_roles": [],
  "canonical_role": "",
  "skills": [],
  "tools": [],
  "soft_skills": [],
  "domains": [],
  "business_families": [],
  "family_confidence": 0.0,
  "seniority": "",
  "experience_level": "",
  "years_experience": null,
  "years_experience_min": null,
  "years_experience_max": null,
  "languages": [],
  "contract_types": [],
  "work_modes": [],
  "locations": [],
  "salary": "",
  "education_level": "",
  "responsibilities": [],
  "requirements": [],
  "evidence": [],
  "warnings": [],
  "confidence": 0.0
}}

Title: {title}
Company: {company}
Source: {source}

Opportunity context:
{context}
""".strip()


def enrich_resume_text(
    text: str,
    *,
    provider: LLMProvider | None = None,
) -> LLMExtractionResult:
    cleaned = clean_resume_semantic_text(text, max_chars=MAX_LLM_INPUT_CHARS)
    if not cleaned:
        return LLMExtractionResult(warnings=["empty_resume_text"])

    llm_provider = provider or get_llm_provider()
    raw_payload = generate_extraction_json(_resume_prompt(cleaned), provider=llm_provider)
    provider_name = getattr(llm_provider, "provider_name", "")
    model = getattr(llm_provider, "model", "")
    return validate_llm_extraction(raw_payload, provider=provider_name, model=model)


def enrich_opportunity_text(
    opportunity: Any,
    *,
    provider: LLMProvider | None = None,
) -> LLMExtractionResult:
    context = _build_opportunity_context(opportunity)
    title = _trim_text(getattr(opportunity, "titre", ""), max_chars=220)
    if not title and not context:
        return LLMExtractionResult(warnings=["empty_opportunity_text"])

    llm_provider = provider or get_llm_provider()
    raw_payload = generate_extraction_json(
        _opportunity_prompt(
            title=title,
            context=context,
            company=getattr(opportunity, "organisation_nom", ""),
            source=_source_name(opportunity),
        ),
        provider=llm_provider,
    )
    provider_name = getattr(llm_provider, "provider_name", "")
    model = getattr(llm_provider, "model", "")
    return validate_llm_extraction(raw_payload, provider=provider_name, model=model)
