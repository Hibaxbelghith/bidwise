from __future__ import annotations

import logging
import re
from typing import Any

from ai.llm.providers import (
    LLMProvider,
    LLMProviderError,
    LLMProviderUnavailable,
    LLMTransientProviderError,
    get_llm_provider,
)


logger = logging.getLogger(__name__)


FRENCH_OUTPUT_MARKERS = (
    " nous ",
    " vous ",
    " votre ",
    " vos ",
    " pour ",
    " dans ",
    " avec ",
    " poste ",
    " profil ",
    " recherche",
    " recherché",
    " recherchée",
    " expérience",
    " compétences",
    " maîtrise",
    " diplôme",
    " comptable",
    " déclarations",
    " fiscal",
    " fiscale",
    " facturation",
    " temps plein",
    " contrat",
)

ENGLISH_OUTPUT_MARKERS = (
    " the ",
    " you ",
    " your ",
    " with ",
    " for ",
    " role ",
    " profile ",
    " experience ",
    " skills ",
    " required ",
    " responsibilities ",
)


RESUME_MATCH_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_markdown": {
            "type": "string",
            "description": "Full Markdown resume match analysis with the required five sections.",
        },
        "verdict": {
            "type": "string",
            "enum": ["strong_match", "good_match", "partial_match", "weak_match", "unclear"],
        },
        "ats_level": {
            "type": "string",
            "enum": ["Good", "Medium", "Low", "Unknown"],
        },
        "next_step": {
            "type": "string",
            "description": "One concrete action the candidate should take before applying.",
        },
    },
    "required": ["analysis_markdown", "verdict", "ats_level", "next_step"],
    "additionalProperties": False,
}


RESUME_OPTIMIZATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "optimization_markdown": {
            "type": "string",
            "description": "Full Markdown CV optimization plan with headings and bullets.",
        },
        "next_step": {
            "type": "string",
            "description": "The best next edit before applying.",
        },
    },
    "required": ["optimization_markdown", "next_step"],
    "additionalProperties": False,
}


RESUME_COVER_LETTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cover_letter_markdown": {
            "type": "string",
            "description": "Full Markdown cover letter response with long and short versions.",
        },
        "next_step": {
            "type": "string",
            "description": "The best next edit before sending the letter.",
        },
    },
    "required": ["cover_letter_markdown", "next_step"],
    "additionalProperties": False,
}


RESUME_SUMMARY_REWRITE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary_markdown": {
            "type": "string",
            "description": "Markdown response with rewritten professional summary options.",
        },
        "next_step": {
            "type": "string",
            "description": "The best next edit before using the summary.",
        },
    },
    "required": ["summary_markdown", "next_step"],
    "additionalProperties": False,
}


RESUME_INTERVIEW_PREP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "interview_markdown": {
            "type": "string",
            "description": "Markdown interview preparation guide with technical, behavioral, and recruiter questions.",
        },
        "next_step": {
            "type": "string",
            "description": "The single most important preparation action before the interview.",
        },
    },
    "required": ["interview_markdown", "next_step"],
    "additionalProperties": False,
}


class ResumeMatchLLMError(RuntimeError):
    """Raised when the resume match assistant cannot produce a safe LLM analysis."""


def generate_resume_match_analysis(
    evidence: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """
    Generate a professional Glassdoor-style resume fit analysis from evidence.

    This function does not parse resumes and does not compute matching itself.
    It only asks the configured LLM provider to write a grounded analysis from
    the structured evidence produced by build_resume_match_evidence().
    """
    if not isinstance(evidence, dict):
        raise ResumeMatchLLMError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ResumeMatchLLMError("Resume match evidence is not ready for LLM analysis.")

    llm_provider = provider or get_llm_provider()
    prompt = build_resume_match_analysis_prompt(evidence)

    match = _dict(evidence.get("match"))
    expected_ats_percent = _dict(match.get("ats")).get("keyword_coverage_percent")
    expected_ats_level = _ats_level_from_percent(
        expected_ats_percent,
    )

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_MATCH_ANALYSIS_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning("Resume match LLM analysis failed provider=%s reason=%s", getattr(llm_provider, "provider_name", ""), exc)
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_analysis_payload(
        payload,
        provider=llm_provider,
        expected_ats_level=expected_ats_level,
        expected_ats_percent=expected_ats_percent,
    )


def generate_resume_optimization(
    evidence: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """
    Generate ATS-friendly CV optimization suggestions from existing evidence.

    This action rewrites suggestions only; it never parses a resume and never
    adds facts that are not visible in the resume/profile evidence.
    """
    if not isinstance(evidence, dict):
        raise ResumeMatchLLMError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ResumeMatchLLMError("Resume match evidence is not ready for CV optimization.")

    llm_provider = provider or get_llm_provider()
    prompt = build_resume_optimization_prompt(evidence)

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_OPTIMIZATION_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "Resume optimization LLM failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_optimization_payload(payload, provider=llm_provider)


def generate_cover_letter(
    evidence: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """
    Generate a grounded motivation letter from existing resume match evidence.

    This action does not infer personal details. It uses placeholders for
    missing name, contact, portfolio, and date fields.
    """
    if not isinstance(evidence, dict):
        raise ResumeMatchLLMError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ResumeMatchLLMError("Resume match evidence is not ready for cover letter generation.")

    llm_provider = provider or get_llm_provider()
    prompt = build_cover_letter_prompt(evidence)

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_COVER_LETTER_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "Cover letter LLM failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_cover_letter_payload(payload, provider=llm_provider)


def generate_deterministic_cover_letter(evidence: dict[str, Any]) -> dict[str, Any]:
    """Build a concise, evidence-only cover letter when every LLM provider fails."""
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    contact = _dict(profile.get("contact"))

    language = _resume_match_output_language(opportunity)
    name = _text(contact.get("full_name"))
    if name == "not visible in resume":
        name = "[Candidate Full Name]" if language == "en" else "[Nom complet]"
    email = _text(contact.get("email"))
    if email == "not visible in resume":
        email = "[Email]"

    title = _text(opportunity.get("title"))
    company = _text(opportunity.get("company"))
    skills = _list_raw(match.get("matching_skills"))[:4]
    tools = _list_raw(resume.get("tools"))[:3]
    gaps = (
        _list_raw(prioritized_gaps.get("critical"))
        + _list_raw(prioritized_gaps.get("useful"))
    )[:2]

    skill_text = ", ".join(skills) if skills else (
        "les compétences comptables visibles dans mon CV"
        if language == "fr"
        else "the relevant skills demonstrated in my resume"
    )
    tool_text = ", ".join(tools)

    if language == "fr":
        tools_sentence = (
            f" Je maîtrise également les outils suivants mentionnés dans mon CV : {tool_text}."
            if tool_text
            else ""
        )
        gap_sentence = (
            " Je souhaite approfondir mes connaissances en "
            + " et ".join(gaps)
            + " dans le cadre de ce poste."
            if gaps
            else ""
        )
        markdown = f"""## Lettre de motivation
{name}
[Ville / Pays]
{email} | [Téléphone]
[Date]

Équipe recrutement
{company}

Bonjour,

Je vous adresse ma candidature au poste de {title} au sein de {company}. Cette opportunité correspond à mon parcours et à mon souhait de poursuivre mon développement professionnel dans ce domaine.

Mon CV met notamment en évidence les compétences suivantes : {skill_text}.{tools_sentence} Ces acquis me permettront de contribuer aux missions décrites dans votre offre avec rigueur et organisation.

{gap_sentence.strip() or "Je souhaite mettre mes compétences au service de votre équipe et continuer à progresser sur les responsabilités du poste."}

Je serais ravie d’échanger avec vous afin de vous présenter plus précisément ma motivation.

Cordialement,

{name}

## Version courte pour candidature en ligne
Je souhaite présenter ma candidature au poste de {title} chez {company}. Mon CV met en évidence {skill_text}, ainsi que des compétences directement pertinentes pour les missions proposées. Je serais ravie d’échanger avec votre équipe au sujet de cette opportunité.

## Notes de personnalisation
- Compléter la date, le numéro de téléphone et la ville avant l’envoi.
- Vérifier chaque compétence et conserver uniquement les éléments correspondant à votre expérience réelle."""
        next_step = "Compléter les coordonnées et vérifier les compétences avant l’envoi."
    else:
        tools_sentence = (
            f" My resume also shows experience with these tools: {tool_text}."
            if tool_text
            else ""
        )
        gap_sentence = (
            " I am interested in developing further knowledge of "
            + " and ".join(gaps)
            + " in this role."
            if gaps
            else ""
        )
        markdown = f"""## Cover Letter
{name}
[City / Country]
{email} | [Phone]
[Date]

Hiring Team
{company}

Dear Hiring Team,

I am applying for the {title} position at {company}. This opportunity aligns with my background and professional development goals.

My resume demonstrates the following relevant skills: {skill_text}.{tools_sentence} These strengths would help me contribute to the responsibilities described in the job posting.

{gap_sentence.strip() or "I look forward to contributing to your team while continuing to develop in the responsibilities of this role."}

I would welcome the opportunity to discuss my application with you.

Sincerely,

{name}

## Short version for online applications
I am applying for the {title} position at {company}. My resume demonstrates {skill_text}, along with experience relevant to the advertised responsibilities. I would welcome the opportunity to discuss my application.

## Personalization notes
- Complete the date, phone number, and city before sending.
- Verify every skill and keep only statements supported by your actual experience."""
        next_step = "Complete the contact details and verify every skill before sending."

    return {
        "status": "ready",
        "source": "deterministic",
        "provider": "",
        "model": "",
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def generate_summary_rewrite(
    evidence: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Generate ATS-friendly professional summary rewrites from evidence."""
    if not isinstance(evidence, dict):
        raise ResumeMatchLLMError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ResumeMatchLLMError("Resume match evidence is not ready for summary rewriting.")

    llm_provider = provider or get_llm_provider()
    prompt = build_summary_rewrite_prompt(evidence)

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_SUMMARY_REWRITE_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "Summary rewrite LLM failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_summary_rewrite_payload(payload, provider=llm_provider)


def generate_deterministic_summary_rewrite(evidence: dict[str, Any]) -> dict[str, Any]:
    """Build safe CV summaries from extracted evidence when the LLM is unavailable."""
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))

    language = _resume_match_output_language(opportunity)
    role = _text(resume.get("canonical_role"))
    if role == "not visible in resume":
        roles = _list_raw(profile.get("target_roles"))
        role = roles[0] if roles else ("Profil professionnel" if language == "fr" else "Professional")
    years = profile.get("experience_years")
    skills = _list_raw(resume.get("skills"))
    tools = _list_raw(resume.get("tools"))
    safe_keywords = _list_raw(ats.get("covered_keywords"))[:8] or skills[:8]
    missing = _list_raw(ats.get("missing_or_weak_keywords"))[:5]

    strongest = skills[:4] or safe_keywords[:4]
    cautious = skills[:3] or safe_keywords[:3]
    experience_phrase = ""
    try:
        if float(years) > 0:
            experience_phrase = (
                f" avec {int(float(years))} ans d'expérience"
                if language == "fr"
                else f" with {int(float(years))} years of experience"
            )
    except (TypeError, ValueError):
        pass

    if language == "fr":
        strong_text = ", ".join(strongest) or "compétences professionnelles pertinentes"
        cautious_text = ", ".join(cautious) or "compétences transférables"
        tool_sentence = f" Maîtrise de {', '.join(tools[:3])}." if tools else ""
        markdown = f"""## Résumé professionnel recommandé
{role}{experience_phrase}, avec des compétences démontrées en {strong_text}.{tool_sentence} Profil rigoureux et organisé, prêt à contribuer aux responsabilités du poste.

## Version plus prudente
{role}{experience_phrase}, avec une solide base en {cautious_text}. Participation aux activités visibles dans le CV et volonté de renforcer progressivement les compétences spécifiques demandées par l'offre.

## Mots-clés ATS à inclure
{chr(10).join(f"- {item}" for item in safe_keywords) or "- Aucun mot-clé vérifié disponible"}

## Mots à éviter
{chr(10).join(f"- {item}" for item in missing) or "- Toute compétence non démontrée dans le CV"}"""
        next_step = "Vérifier que chaque compétence du résumé est démontrée dans le CV."
    else:
        strong_text = ", ".join(strongest) or "relevant professional skills"
        cautious_text = ", ".join(cautious) or "transferable skills"
        tool_sentence = f" Proficient with {', '.join(tools[:3])}." if tools else ""
        markdown = f"""## Recommended professional summary
{role}{experience_phrase}, demonstrating skills in {strong_text}.{tool_sentence} Organized and detail-oriented, ready to contribute to the responsibilities of this role.

## More cautious version
{role}{experience_phrase}, with a solid foundation in {cautious_text}. Experience supporting the activities visible in the resume and motivation to develop the role-specific skills requested by the employer.

## ATS keywords to include
{chr(10).join(f"- {item}" for item in safe_keywords) or "- No verified keywords available"}

## Words to avoid
{chr(10).join(f"- {item}" for item in missing) or "- Any skill not demonstrated in the resume"}"""
        next_step = "Verify that every skill in the summary is demonstrated in the resume."

    return {
        "status": "ready",
        "source": "deterministic",
        "provider": "",
        "model": "",
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def generate_interview_prep(
    evidence: dict[str, Any],
    *,
    provider: LLMProvider | None = None,
) -> dict[str, Any]:
    """Generate grounded HR and technical interview preparation from evidence."""
    if not isinstance(evidence, dict):
        raise ResumeMatchLLMError("Resume match evidence must be a dictionary.")
    if str(evidence.get("status") or "").upper() != "READY":
        raise ResumeMatchLLMError("Resume match evidence is not ready for interview preparation.")

    llm_provider = provider or get_llm_provider()
    prompt = build_interview_prep_prompt(evidence)

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_INTERVIEW_PREP_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning(
            "Interview prep LLM failed provider=%s reason=%s",
            getattr(llm_provider, "provider_name", ""),
            exc,
        )
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_interview_prep_payload(payload, provider=llm_provider)


def build_resume_match_analysis_prompt(evidence: dict[str, Any]) -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    role_alignment = _dict(match.get("role_alignment"))
    seniority_alignment = _dict(match.get("seniority_alignment"))
    location_alignment = _dict(match.get("location_alignment"))
    contract_alignment = _dict(match.get("contract_alignment"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    critical_gaps = prioritized_gaps.get("critical", [])
    useful_gaps = prioritized_gaps.get("useful", [])
    optional_gaps = prioritized_gaps.get("optional", [])
    output_language = _resume_match_output_language(opportunity)
    language_rule = _resume_match_analysis_language_rule(output_language)
    section_headings = _resume_match_section_headings(output_language)
    opening_sentence = (
        'Start with "Le CV montre ..."'
        if output_language == "fr"
        else 'Start with "Your resume shows ..."'
    )
    ats_line_label = (
        "Niveau compatibilité ATS"
        if output_language == "fr"
        else "ATS compatibility level"
    )
    covered_keywords_label = "Mots-clés couverts" if output_language == "fr" else "Keywords covered"
    missing_keywords_label = "Mots-clés manquants" if output_language == "fr" else "Missing keywords"
    ats_level_values = (
        "Bon, Moyen, Faible, Inconnu"
        if output_language == "fr"
        else "Good, Medium, Low, Unknown"
    )
    candidate_data_block = _build_candidate_data_block(
        profile,
        resume,
        include_profile_skills=True,
        include_preferences=True,
        include_contract_types=True,
        resume_heading="Resume signals detected",
        canonical_role_label="Canonical role in resume",
        skills_label="Skills in resume",
        tools_label="Tools in resume",
        domains_label="Domains in resume",
    )
    job_data_block = _build_job_opportunity_data_block(
        opportunity,
        include_location=True,
        include_contract=True,
        include_experience=True,
        include_education=True,
    )

    # Keep the LLM grounded with neutral signals only. Do not pass generated
    # reason strings or pre-computed bullets here, otherwise the model tends to
    # copy generic labels instead of writing a role-specific analysis.
    return f"""
You are BidWise AI, a senior recruitment and ATS (Applicant Tracking System) expert.

ABSOLUTE RULE: Use ONLY the structured data provided below.
Never invent experience, certifications, tools, or achievements.
If information is missing, write "not visible in resume".
Profile-declared skills and target roles are preferences only. Never present
them as skills or experience demonstrated by the resume.
Never present a missing or weak keyword as a strength elsewhere in the response.
Before returning, verify that the strengths, gaps, ATS keywords, and next step
do not contradict each other and do not mention technologies absent from the data.

LANGUAGE RULE:
{language_rule}
- Keep JSON field names unchanged: analysis_markdown, verdict, ats_level, next_step.
- The verdict and ats_level JSON fields must keep their schema values in English.
- Escape apostrophes and accents normally as valid JSON string content.
- Never mix languages in analysis_markdown or next_step.

{candidate_data_block}

{job_data_block}

==================================================
BIDWISE MATCHING SIGNALS
==================================================
BidWise match score: {_text(match.get("fit_score"))}%

Role alignment
- Level: {_text(role_alignment.get("level"))}
- Canonical role in resume: {_text(resume.get("canonical_role"))}
- Target roles in profile: {_list(profile.get("target_roles"))}
- Role in job posting: {_text(opportunity.get("title"))}

Seniority alignment
- Level: {_text(seniority_alignment.get("level"))}
- Profile experience years: {_text(profile.get("experience_years"))}
- Required by job posting: {_nested(opportunity, "experience", "min")} - {_nested(opportunity, "experience", "max")} years

Location alignment
- Level: {_text(location_alignment.get("level"))}
- Preferred locations: {_list(profile.get("locations"))}
- Job location: {_text(opportunity.get("location"))}

Contract alignment
- Level: {_text(contract_alignment.get("level"))}
- Contracts sought: {_list(profile.get("employment_types"))}
- Job contract: {_text(opportunity.get("contract"))}

Matched skills: {_list(match.get("matching_skills"))}
Keywords present in resume: {_list(ats.get("covered_keywords"))}
Missing or weak keywords: {_list(ats.get("missing_or_weak_keywords"))}
ATS coverage: {_text(ats.get("keyword_coverage_percent"))}%

BidWise prioritized gaps
- Critical (required in skills AND requirements): {_list(critical_gaps)}
- Useful (mentioned in skills or requirements): {_list(useful_gaps)}
- Optional (context only): {_list(optional_gaps)}

ABSOLUTE ATS RULE:
- The BidWise ATS score is {_text(ats.get("keyword_coverage_percent"))}%.
- Use this value exactly. Do not recalculate it.
- If score >= 70%: write exactly "Good".
- If score >= 40% and < 70%: write exactly "Medium".
- If score < 40%: write exactly "Low".
- The ats_level JSON field must follow this rule.
- In analysis_markdown, write the ATS compatibility label using: {ats_level_values}.

==================================================
EXPECTED OUTPUT - EXACT STRUCTURE
==================================================

Return only a valid JSON object with these fields:
- analysis_markdown
- verdict
- ats_level
- next_step

The analysis_markdown field must contain exactly these Markdown sections.
Maximum 650 words total.

{section_headings[0]}
2 to 3 direct sentences.
{opening_sentence}.
State clearly whether this is a strong match, partial match, or weak match.

{section_headings[1]}
Bullet points only.
Each bullet: short bold title + concrete explanation tied to the job posting.
Minimum 2 bullets, maximum 4.
Do NOT use generic titles such as "Role alignment", "Relevant keywords", or "Experience fit".
Each bullet must name a real skill, tool, domain, or concrete signal from the resume.
Good example:
- **Python and Apache Spark** - Resume shows these technologies, directly aligned with the ETL pipeline requirements in the job posting.
Bad example:
- **Role alignment** - Role evidence overlaps with the opportunity.

{section_headings[2]}
Bullet points only.
Each bullet: short bold title + detailed gap explanation + impact on the application.
Cover at least 2 critical gaps first, then 1 useful gap if available.
Prioritize specific technologies (tools, platforms, languages, frameworks) over generic skills.
For each gap, explain: what the job requires, what the resume shows instead, and the ATS or recruiter impact.
Good example:
- **[Missing tool] not mentioned** - The job lists this tool as required, while the resume does not show it. Its absence may reduce ATS visibility.
Bad example:
- **API not mentioned** - The job requires API.

{section_headings[3]}
- BidWise ATS Score: {_text(ats.get("keyword_coverage_percent"))}%
- {covered_keywords_label}: list the matched keywords
- {missing_keywords_label}: critical gaps first, then useful gaps
- {ats_line_label}: apply the ABSOLUTE ATS RULE above + one sentence explanation

{section_headings[4]}
One concrete and specific action to take before applying.
Start with an action verb.
Cover the 2 or 3 most critical gaps, not a single isolated keyword.
Good example:
Add a Technical Skills section covering the two most important missing job keywords, using "add only if true" for anything not proven by the resume.

The verdict field must be one of: strong_match, good_match, partial_match, weak_match, unclear.
The ats_level field must follow the ABSOLUTE ATS RULE.
The next_step field must restate the Next step section as one short sentence.
""".strip()


def build_resume_optimization_prompt(evidence: dict[str, Any]) -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    output_language = _resume_match_output_language(opportunity)
    language_rule = _resume_match_action_language_rule(
        output_language,
        markdown_field="optimization_markdown and next_step",
    )
    summary_style_rule = _resume_cv_summary_style_rule(output_language)
    section_headings = _resume_optimization_section_headings(output_language)
    candidate_data_block = _build_candidate_data_block(
        profile,
        resume,
        include_profile_skills=True,
        include_preferences=True,
        include_contract_types=True,
        resume_heading="Resume signals",
        canonical_role_label="Canonical role",
        redact_resume_excerpt=True,
    )
    job_data_block = _build_job_opportunity_data_block(
        opportunity,
        include_location=True,
        include_contract=True,
        include_experience=True,
    )

    return f"""
You are BidWise AI, a senior recruitment and ATS (Applicant Tracking System) expert
specializing in CV optimization.

Your task: produce concrete CV optimization suggestions tailored to this job posting.

ABSOLUTE RULES:
- Use only the structured data provided below.
- Never invent experience, certifications, tools, degrees, or achievements.
- Profile-declared skills and target roles are preferences only. Never include
  them as CV skills unless they are also visible in the resume signals.
- For any critical technology absent from the resume, suggest honest wording only:
  "exposure", "basic knowledge", "personal project", or "academic project" -
  only if the provided data supports it. Otherwise write "add only if true".
- All suggestions must be directly copy-pasteable into a CV.
- ATS format: plain text, no tables, no icons, no complex layout.
- Do not rewrite the entire CV. Suggest only the sections that need improvement.
- Maximum 700 words total.

LANGUAGE RULE:
{language_rule}

{summary_style_rule}

{candidate_data_block}

{job_data_block}

==================================================
BIDWISE SIGNALS
==================================================
CV vs job match score: {_text(match.get("fit_score"))}%
Keywords present in resume: {_list(ats.get("covered_keywords"))}
Missing or weak keywords: {_list(ats.get("missing_or_weak_keywords"))}
Critical gaps (required in skills AND requirements): {_list(prioritized_gaps.get("critical"))}
Useful gaps (mentioned in skills or requirements): {_list(prioritized_gaps.get("useful"))}
Optional gaps (context only): {_list(prioritized_gaps.get("optional"))}

==================================================
EXPECTED OUTPUT
==================================================
Return only a valid JSON object with these fields:
- optimization_markdown
- next_step

The optimization_markdown field must contain exactly these Markdown sections:
Tone: practical, professional, and copy-paste oriented.
Start directly with the first Markdown section. Do not add a greeting before the first heading.

{section_headings[0]}
Give exactly 2 CV title options.
- Option 1: strong version based on skills visible in the resume.
- Option 2: cautious version if critical gaps cannot be proven.

{section_headings[1]}
3 to 5 professional lines.
Highlight the strongest evidence from the resume.
Include job keywords only if they are visible in the resume or honestly qualifiable.

{section_headings[2]}
4 to 6 skill lines.
Style example: "Data Engineering: ETL/ELT pipelines, SQL, data quality"
Do not list any technology as mastered if it is absent from the resume.

{section_headings[3]}
4 to 6 experience bullets.
Each bullet starts with an action verb.
Each bullet must be defensible from the resume data or framed as a conditional suggestion.
If a bullet depends on unproven experience, start with: "If applicable:"

{section_headings[4]}
2 to 4 honest phrasings for critical or useful gaps.
Goal: help the candidate pass ATS filters without misrepresenting their background.
Example: "Exposure to [missing tool] through an academic project" - only if compatible with the data.

{section_headings[5]}
3 to 5 short tips to make the CV more ATS-friendly.
Include guidance on keyword placement in the top third of the CV.

{section_headings[6]}
One priority action to take before applying.

The next_step field must restate the same priority action as one short sentence.
""".strip()


def build_summary_rewrite_prompt(evidence: dict[str, Any]) -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    output_language = _resume_match_output_language(opportunity)
    language_rule = _resume_match_action_language_rule(
        output_language,
        markdown_field="summary_markdown and next_step",
    )
    summary_style_rule = _resume_cv_summary_style_rule(output_language)
    section_headings = _resume_summary_section_headings(output_language)
    candidate_data_block = _build_candidate_data_block(
        profile,
        resume,
        include_profile_skills=True,
        resume_heading="Resume signals",
        canonical_role_label="Canonical role",
        resume_excerpt_label="Current resume excerpt",
    )
    job_data_block = _build_job_opportunity_data_block(opportunity)

    return f"""
You are BidWise AI, a senior recruiter and ATS resume optimization expert.

Your task: rewrite the professional summary for this resume and job opportunity.

ABSOLUTE RULES:
- Use only the structured evidence below.
- Never invent experience, certifications, tools, achievements, or years of experience.
- Profile-declared skills and target roles are preferences only. Never include
  them in the rewritten summary unless they are also visible in the resume signals.
- If a skill is missing, do not claim mastery. Use honest wording such as "exposure to" only if supported.
{language_rule}
- Make the summaries ATS-friendly, recruiter-friendly, and directly copy-pasteable.
- Maximum 450 words total.

{summary_style_rule}

{candidate_data_block}

{job_data_block}

==================================================
BIDWISE ATS SIGNALS
==================================================
CV vs job match score: {_text(match.get("fit_score"))}%
Keywords present in resume: {_list(ats.get("covered_keywords"))}
Missing or weak keywords: {_list(ats.get("missing_or_weak_keywords"))}
Critical gaps: {_list(prioritized_gaps.get("critical"))}
Useful gaps: {_list(prioritized_gaps.get("useful"))}

==================================================
EXPECTED OUTPUT
==================================================
Return only a valid JSON object with these fields:
- summary_markdown
- next_step

The summary_markdown field must contain exactly these Markdown sections:
Tone: practical, professional, and ATS-focused.
Start directly with the first Markdown section. Do not add a greeting before the first heading.

{section_headings[0]}
Write one polished 3 to 4 line summary tailored to the job.

{section_headings[1]}
Write one honest version for cases where some job keywords are not strongly proven in the resume.
When the candidate is changing careers, connect only genuine transferable skills
from the resume to the target role and clearly state that direct experience is not yet proven.
It must still be tailored to the target role and must not simply repeat the original resume summary.
This cautious version MUST be materially different from the recommended summary:
- Use different wording and sentence order.
- Mention only directly proven strengths first.
- Include at least two cautious phrases such as "participation à", "appui à",
  "première exposition à", "bases en", "à renforcer", "selon expérience réelle",
  or their equivalent in the required output language.
- Do not claim direct ownership of missing or weak keywords.
Bad output: recommended summary and cautious summary are identical.
Good output: recommended summary is confident; cautious summary narrows claims and frames weak gaps as support, exposure, or learning areas.

{section_headings[2]}
List 5 to 8 keywords that are safe to include based on the resume evidence.

{section_headings[3]}
List 3 to 5 claims that the candidate should avoid unless they are true.

The next_step field must contain the single most important edit before using the summary.
""".strip()


def build_interview_prep_prompt(evidence: dict[str, Any]) -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))
    ats = _dict(match.get("ats"))
    output_language = _resume_match_output_language(opportunity)
    language_rule = _resume_match_action_language_rule(
        output_language,
        markdown_field="interview_markdown and next_step",
    )
    section_headings = _resume_interview_section_headings(output_language)
    interview_labels = _resume_interview_format_labels(output_language)
    candidate_data_block = _build_candidate_data_block(
        profile,
        resume,
        include_profile_skills=False,
        resume_heading="Resume signals",
        canonical_role_label=None,
        skills_label="Resume skills",
        tools_label="Resume tools",
        domains_label="Resume domains",
    )
    job_data_block = _build_job_opportunity_data_block(opportunity)

    return f"""
You are BidWise AI, a senior HR interview coach with 15 years of experience
in technical and behavioral interviews.

ABSOLUTE RULE: Use ONLY the structured data provided.
Never invent experience, certifications, tools, or achievements.
Every question must be grounded in a real gap or signal from the evidence.
Avoid awkward or unrealistic scenarios. Do not mention money loss, fraud, serious client incidents,
or sensitive claims unless explicitly present in the job description or resume evidence.
The answer strategy is coaching, not a fabricated candidate answer.
Never write "I use", "I prepare", "I managed", or any first-person claim unless that exact
experience is visible in the resume evidence. For an unproven gap, explicitly recommend:
acknowledge limited direct experience, cite the closest proven experience, and explain how to learn it.

LANGUAGE RULE:
{language_rule}

{candidate_data_block}

{job_data_block}

==================================================
BIDWISE GAP SIGNALS
==================================================
Critical gaps: {_list(prioritized_gaps.get("critical"))}
Useful gaps: {_list(prioritized_gaps.get("useful"))}
Matched skills: {_list(match.get("matching_skills"))}
ATS coverage: {_text(ats.get("keyword_coverage_percent"))}%

==================================================
EXPECTED OUTPUT - EXACT STRUCTURE
==================================================

Return only a valid JSON object with:
- interview_markdown
- next_step

The interview_markdown field must contain exactly these Markdown sections.
Maximum 450 words total. Be concise and avoid long examples.
Use real newline characters between every heading and paragraph.
Never output literal "\\n" text.

{section_headings[0]}
Generate 2 questions the interviewer will likely ask about the critical gaps.
Use this exact format for each question:
### {interview_labels["technical_label"]}
**{interview_labels["question"]}:** The exact question
**{interview_labels["why"]}:** Which gap it targets, in one sentence
**{interview_labels["answer"]}:** One short answer strategy

{section_headings[1]}
Generate 2 questions about soft skills and work style relevant to this role.
Each question must reference a specific responsibility from the job posting.
Use this exact format for each question:
### {interview_labels["behavioral_label"]}
**{interview_labels["question"]}:** The exact question
**{interview_labels["star"]}:** A concise Situation, Task, Action, Result answer direction

{section_headings[2]}
Generate 2 smart questions the candidate should ask to show genuine interest
and technical depth. Based only on the job description and company data.
Format each question as a Markdown bullet beginning with "- ".

{section_headings[3]}
List 2 potential red flags the recruiter may raise based on the gaps,
with a short honest response strategy for each.
Use this exact format for each red flag:
### {interview_labels["red_flag_label"]}
**{interview_labels["strategy"]}:** A short honest response strategy

{section_headings[4]}
One concrete action to take in the 48 hours before the interview.

The next_step field must contain the same one-line preparation tip as a short sentence.
""".strip()


def build_cover_letter_prompt(evidence: dict[str, Any]) -> str:
    profile = _dict(evidence.get("profile"))
    resume = _dict(evidence.get("resume"))
    opportunity = _dict(evidence.get("opportunity"))
    match = _dict(evidence.get("match"))
    ats = _dict(match.get("ats"))
    prioritized_gaps = _dict(match.get("prioritized_gaps"))

    # Pre-compute keyword obligations so the prompt is explicit about what
    # must appear in the letter body. This prevents Gemini from omitting
    # critical keywords that ATS systems scan for.
    matched = _list_raw(match.get("matching_skills")) or []
    critical = _list_raw(prioritized_gaps.get("critical")) or []
    useful = _list_raw(prioritized_gaps.get("useful")) or []

    # Only proven matched keywords are mandatory in the letter body. Critical
    # gaps must be framed honestly and must never be presented as experience.
    must_include = matched[:6]
    # Keywords that SHOULD appear if a natural sentence allows it
    should_include = useful[:3]

    job_title_exact = _text(opportunity.get("title"))
    contact = _dict(profile.get("contact"))
    candidate_name = _text(contact.get("full_name")) or "[Candidate Full Name]"
    verified_email = _text(contact.get("email")) or "[Email]"
    output_language = _resume_match_output_language(opportunity)
    language_rule = _resume_match_action_language_rule(
        output_language,
        markdown_field="cover_letter_markdown and next_step",
    )
    section_headings = _resume_cover_letter_section_headings(output_language)
    salutation = "Bonjour," if output_language == "fr" else "Dear Hiring Team,"
    closing = "Cordialement," if output_language == "fr" else "Sincerely,"
    action_verbs = (
        "réaliser, structurer, suivre, préparer, contrôler, mettre à jour, collaborer, optimiser"
        if output_language == "fr"
        else "Built, Designed, Delivered, Led, Developed, Automated, Implemented, Maintained, Optimized, Collaborated"
    )
    action_verb_rule = (
        f"Use professional natural French. Include action verbs such as {action_verbs}, but do not start every paragraph with a forced past participle."
        if output_language == "fr"
        else f"Every paragraph must start with or contain a strong action verb in the first sentence. Use: {action_verbs}."
    )
    gap_framing_sentence = (
        '"Je renforce actuellement mes connaissances en [mot-clé manquant] et je souhaite les appliquer dans ce poste."'
        if output_language == "fr"
        else '"I am currently deepening my knowledge of [gap keyword] and look forward to applying it in this role."'
    )
    candidate_data_block = _build_candidate_data_block(
        profile,
        resume,
        contact_lines=[
            "Candidate contact data:",
            f"- Full name: {candidate_name}",
            f"- Verified email: {verified_email}",
        ],
        include_profile_skills=True,
        include_preferences=True,
        locations_label="Locations",
        resume_heading="Resume signals",
        canonical_role_label="Canonical role",
        redact_resume_excerpt=True,
    )
    job_data_block = _build_job_opportunity_data_block(
        opportunity,
        title=job_title_exact,
        include_location=True,
        include_contract=True,
        include_experience=True,
    )

    return f"""
You are BidWise AI, a senior recruiter and ATS-optimized cover letter specialist.

Your task: write a tailored, ATS-strong motivation letter for this job opportunity.

ABSOLUTE RULES:
- Use only the structured evidence below.
- Never invent employment history, certifications, achievements, tools, salary, or personal details.
- Profile-declared skills and target roles are preferences only. Never claim
  them in the letter unless they are also visible in the resume signals.
- If name, email, phone, portfolio, or date are not visible, use placeholders.
- Use the verified candidate email from CANDIDATE CONTACT DATA exactly when it is available.
- Do not extract or reuse another email address from the resume excerpt if a verified email is available.
- If a skill is absent from the resume, do not claim mastery. Use honest framing instead.
- Do not say the candidate is currently in an internship or current job unless the structured resume evidence explicitly proves it.
- Do not claim immediate availability, a notice period, or a preferred start date because these facts are not supplied.
{language_rule}
- Maximum 450 words total across both letter versions combined.

ATS RULES - these directly affect whether the letter passes automated screening:

1. JOB TITLE RULE: The exact job title "{job_title_exact}" must appear word for word
   in the first paragraph. ATS systems match on exact title strings.

2. KEYWORD DENSITY RULE: Every keyword in the MUST INCLUDE list below must appear
   at least once in the full cover letter body. Embed them naturally in sentences.
   Do not list them. Do not force them awkwardly.
   MUST INCLUDE: {", ".join(must_include) if must_include else "see matched skills above"}

3. SHOULD INCLUDE: Include these in the letter if a natural sentence allows it.
   SHOULD INCLUDE: {", ".join(should_include) if should_include else "none"}

4. GAP FRAMING RULE: For each critical gap keyword that is absent from the resume,
   include one honest sentence in paragraph 4 or 5 using this pattern:
   {gap_framing_sentence}
   Only use this for gaps listed as critical.
   Critical gaps: {_list(critical[:3])}
   Never say or imply that the candidate performed, prepared, mastered, or regularly
   used a critical gap keyword when it is absent from the resume evidence.

5. ACTION VERB RULE: {action_verb_rule}

6. SHORT VERSION ATS RULE: The short version must also contain the exact job title
   and at least 3 keywords from the MUST INCLUDE list. Recruiters who paste only
   the short version into an ATS must still get a keyword match.

PARAGRAPH QUALITY STANDARD:

Weak paragraph (never write like this):
"I am a motivated professional with strong communication skills and a passion for technology.
I believe I would be a great fit for your team."

Strong paragraph (write like this):
"Over the past two years, I built and maintained ETL pipelines using Python and Apache Airflow,
processing daily data feeds into a PostgreSQL warehouse. This experience maps directly to the
data pipeline responsibilities described in the {job_title_exact} role at {_text(opportunity.get("company"))}."

The difference: strong paragraphs name the exact job title, specific tools from the resume,
and connect them to a specific responsibility in the job posting.

FINAL FACT CHECK:
- Every employment history item, employer, tool, responsibility, and achievement in the letter
  must be traceable to the Resume signals block.
- Do not create an employer name from the opportunity, profile, or general context.
- Do not turn "participation", "support", "exposure", or a missing keyword into direct ownership.
- If the resume evidence does not prove a fact, omit it or label it as a learning objective.

{candidate_data_block}

{job_data_block}

==================================================
EXPECTED OUTPUT
==================================================
Return only a valid JSON object with fields: cover_letter_markdown and next_step.

{section_headings[0]}
{candidate_name}
[City / Country]
{verified_email} | [Phone] | [Portfolio or GitHub link]
[Date]

{"Équipe recrutement" if output_language == "fr" else "Hiring Team"}
{_text(opportunity.get("company"))}

{salutation}

Write 4 concise paragraphs:
Paragraph 1: State the exact role title and company. Express clear interest.
Paragraph 2: Connect the 2 or 3 strongest proven resume skills and tools to the core requirements.
Paragraph 3: Describe one relevant proven responsibility, then address critical gaps honestly if any exist.
Paragraph 4: Close with a professional call to action.

{closing}
[Candidate Full Name]

{section_headings[1]}
2 short paragraphs. Must contain the exact job title and at least 3 keywords from the MUST INCLUDE list.
Paragraph 1: Role, company, and strongest match signal.
Paragraph 2: Two or three proven skills or tools, motivation, and call to action.

{section_headings[2]}
2 short bullets: what placeholders or unverifiable facts the candidate must check before sending.

The next_step field: the single most impactful keyword or fact the candidate should add before sending.
""".strip()


def _build_candidate_data_block(
    profile: dict[str, Any],
    resume: dict[str, Any],
    *,
    contact_lines: list[str] | None = None,
    include_profile_skills: bool = True,
    include_preferences: bool = False,
    include_contract_types: bool = False,
    locations_label: str = "Preferred locations",
    resume_heading: str = "Resume signals",
    canonical_role_label: str | None = "Canonical role",
    skills_label: str = "Skills",
    tools_label: str = "Tools",
    domains_label: str = "Domains",
    resume_excerpt_label: str = "Resume excerpt",
    redact_resume_excerpt: bool = False,
) -> str:
    excerpt = _text(resume.get("summary_excerpt"))
    if redact_resume_excerpt:
        excerpt = _redact_contact_details(excerpt)

    lines = [
        "==================================================",
        "CANDIDATE DATA",
        "==================================================",
    ]
    if contact_lines:
        lines.extend(str(line).rstrip() for line in contact_lines if str(line or "").strip())
        lines.append("")

    lines.extend(
        [
            f"Target role: {_list(profile.get('target_roles'))}",
            f"Level: {_text(profile.get('experience_level'))} - {_text(profile.get('experience_years'))} years",
        ]
    )
    if include_profile_skills:
        lines.append(
            "Profile-declared skills (context only, not resume evidence): "
            f"{_list(profile.get('skills'))}"
        )
    if include_preferences:
        lines.append(f"{locations_label}: {_list(profile.get('locations'))}")
    if include_contract_types:
        lines.append(f"Contract types sought: {_list(profile.get('employment_types'))}")

    lines.extend(["", f"{resume_heading}:"])
    if canonical_role_label:
        lines.append(f"- {canonical_role_label}: {_text(resume.get('canonical_role'))}")
    lines.extend(
        [
            f"- {skills_label}: {_list(resume.get('skills'))}",
            f"- {tools_label}: {_list(resume.get('tools'))}",
            f"- {domains_label}: {_list(resume.get('domains'))}",
            f"- {resume_excerpt_label}: {excerpt}",
        ]
    )
    return "\n".join(lines)


def _build_job_opportunity_data_block(
    opportunity: dict[str, Any],
    *,
    title: str | None = None,
    include_location: bool = False,
    include_contract: bool = False,
    include_experience: bool = False,
    include_education: bool = False,
    include_required_skills: bool = True,
    include_responsibilities: bool = True,
    include_requirements: bool = True,
    include_description: bool = True,
) -> str:
    lines = [
        "==================================================",
        "JOB OPPORTUNITY DATA",
        "==================================================",
        f"Title: {title or _text(opportunity.get('title'))}",
        f"Company: {_text(opportunity.get('company'))}",
    ]
    if include_location:
        lines.append(f"Location: {_text(opportunity.get('location'))}")
    if include_contract:
        lines.append(f"Contract: {_text(opportunity.get('contract'))}")
    if include_experience:
        lines.append(
            "Experience required: "
            f"{_nested(opportunity, 'experience', 'min')} - "
            f"{_nested(opportunity, 'experience', 'max')} years"
        )
    if include_education:
        lines.append(f"Education: {_text(opportunity.get('education'))}")
    if include_required_skills:
        lines.append(f"Required skills: {_list(opportunity.get('skills'))}")
    if include_responsibilities:
        lines.append(f"Responsibilities: {_list(opportunity.get('responsibilities'))}")
    if include_requirements:
        lines.append(f"Requirements: {_list(opportunity.get('requirements'))}")
    if include_description:
        lines.append(f"Description excerpt: {_text(opportunity.get('description_excerpt'))}")
    return "\n".join(lines)


def _normalize_analysis_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
    expected_ats_level: str,
    expected_ats_percent: Any,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResumeMatchLLMError("Resume match LLM payload must be a dictionary.")

    analysis_markdown = _extract_analysis_markdown(payload)
    if not analysis_markdown:
        logger.warning(
            "Resume match LLM payload missing analysis_markdown keys=%s",
            sorted(str(key) for key in payload.keys()),
        )
        raise ResumeMatchLLMError("Resume match LLM payload is missing analysis_markdown.")
    if not _analysis_markdown_is_complete(analysis_markdown):
        logger.warning(
            "Resume match LLM payload incomplete keys=%s markdown_prefix=%r",
            sorted(str(key) for key in payload.keys()),
            analysis_markdown[:180],
        )
        raise ResumeMatchLLMError("Resume match LLM payload is incomplete.")

    verdict = str(payload.get("verdict") or "unclear").strip() or "unclear"
    ats_level = expected_ats_level or str(payload.get("ats_level") or "Unknown").strip() or "Unknown"
    next_step = str(payload.get("next_step") or "").strip()
    analysis_markdown = _force_ats_score_in_markdown(analysis_markdown, expected_ats_percent)
    analysis_markdown = _force_ats_level_in_markdown(analysis_markdown, ats_level)

    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(provider, "provider_name", ""),
        "model": getattr(provider, "model", ""),
        "analysis_markdown": analysis_markdown,
        "verdict": verdict,
        "ats_level": ats_level,
        "next_step": next_step,
    }


def _normalize_optimization_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResumeMatchLLMError("Resume optimization LLM payload must be a dictionary.")

    markdown = _extract_optimization_markdown(payload)
    if not markdown:
        logger.warning(
            "Resume optimization LLM payload missing markdown keys=%s",
            sorted(str(key) for key in payload.keys()),
        )
        raise ResumeMatchLLMError("Resume optimization LLM payload is missing optimization content.")

    next_step = str(payload.get("next_step") or "").strip()
    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(provider, "provider_name", ""),
        "model": getattr(provider, "model", ""),
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def _normalize_summary_rewrite_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResumeMatchLLMError("Summary rewrite LLM payload must be a dictionary.")

    markdown = _extract_summary_markdown(payload)
    if not markdown:
        logger.warning(
            "Summary rewrite LLM payload missing markdown keys=%s",
            sorted(str(key) for key in payload.keys()),
        )
        raise ResumeMatchLLMError("Summary rewrite LLM payload is missing summary content.")

    next_step = str(payload.get("next_step") or "").strip()
    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(provider, "provider_name", ""),
        "model": getattr(provider, "model", ""),
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def _normalize_cover_letter_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResumeMatchLLMError("Cover letter LLM payload must be a dictionary.")

    markdown = _extract_cover_letter_markdown(payload)
    if not markdown:
        logger.warning(
            "Cover letter LLM payload missing markdown keys=%s",
            sorted(str(key) for key in payload.keys()),
        )
        raise ResumeMatchLLMError("Cover letter LLM payload is missing cover letter content.")
    next_step = str(payload.get("next_step") or "").strip()
    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(provider, "provider_name", ""),
        "model": getattr(provider, "model", ""),
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def _normalize_interview_prep_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ResumeMatchLLMError("Interview prep LLM payload must be a dictionary.")

    markdown = _extract_interview_markdown(payload)
    if not markdown:
        logger.warning(
            "Interview prep LLM payload missing markdown keys=%s",
            sorted(str(key) for key in payload.keys()),
        )
        raise ResumeMatchLLMError("Interview prep LLM payload is missing interview content.")

    next_step = str(payload.get("next_step") or "").strip()
    return {
        "status": "ready",
        "source": "llm",
        "provider": getattr(provider, "provider_name", ""),
        "model": getattr(provider, "model", ""),
        "analysis_markdown": markdown,
        "next_step": next_step,
    }


def _extract_analysis_markdown(payload: dict[str, Any]) -> str:
    for key in (
        "analysis_markdown",
        "markdown",
        "analysis",
        "answer",
        "response",
        "content",
        "message",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_generated_markdown(value)

    section_markdown = _sectioned_payload_to_markdown(payload)
    if section_markdown:
        return section_markdown

    analysis = payload.get("analysis")
    if isinstance(analysis, dict):
        return _sectioned_payload_to_markdown(analysis)

    return ""


def _extract_summary_markdown(payload: dict[str, Any]) -> str:
    for key in ("summary_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_generated_markdown(value)
    return ""


def _extract_cover_letter_markdown(payload: dict[str, Any]) -> str:
    for key in ("cover_letter_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_generated_markdown(value)
    return ""


def _extract_interview_markdown(payload: dict[str, Any]) -> str:
    for key in ("interview_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_generated_markdown(value)
    return ""


def _normalize_generated_markdown(value: str) -> str:
    markdown = value.strip()
    if "\\n" in markdown:
        markdown = markdown.replace("\\r\\n", "\n").replace("\\n", "\n")
    markdown = re.sub(r"(?<!\n)(##\s+)", r"\n\n\1", markdown)
    section_titles = (
        "1. Global verdict",
        "2. Where you are a strong fit",
        "3. What to watch out for",
        "4. ATS analysis",
        "5. Next step",
        "Updated headline",
        "Updated summary",
        "Updated core skills section",
        "Resume bullets to strengthen this application",
        "Honest wording for missing or partial skills",
        "ATS cleanup notes",
        "Best next move",
        "Titre de profil proposé",
        "Résumé professionnel optimisé",
        "Section compétences à renforcer",
        "Expériences à reformuler pour cette offre",
        "Formulations honnêtes pour les compétences partielles",
        "Notes de nettoyage ATS",
        "Meilleure prochaine action",
        "Recommended professional summary",
        "More cautious version",
        "ATS keywords to include",
        "Words to avoid",
        "Résumé professionnel recommandé",
        "Version plus prudente",
        "Mots-clés ATS à inclure",
        "Mots à éviter",
        "Cover Letter",
        "Short version for online applications",
        "Personalization notes",
        "Lettre de motivation",
        "Version courte pour candidature en ligne",
        "Notes de personnalisation",
    )
    for title in section_titles:
        markdown = re.sub(
            rf"(?im)^(?:##\s*)?{re.escape(title)}\s*",
            f"## {title}\n",
            markdown,
        )
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown


def _extract_optimization_markdown(payload: dict[str, Any]) -> str:
    for key in ("optimization_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_generated_markdown(value)

    sections = []
    headline_options = _first_list(payload, ("headline_options", "headlines"))
    if headline_options:
        sections.append(
            "## Updated headline\n"
            + "\n".join(f"- {item}" for item in headline_options[:3])
        )

    summary = _first_text(payload, ("professional_summary", "summary", "updated_summary"))
    if summary:
        sections.append(f"## Updated summary\n{summary}")

    core_skills = _first_list(payload, ("core_skills", "skills_section", "updated_skills"))
    if core_skills:
        sections.append(
            "## Updated core skills section\n"
            + "\n".join(f"- {item}" for item in core_skills)
        )

    bullets = _first_list(payload, ("experience_bullets", "resume_bullets", "bullets"))
    if bullets:
        sections.append(
            "## Resume bullets to strengthen this application\n"
            + "\n".join(f"- {item}" for item in bullets)
        )

    honest_phrasing = _first_list(payload, ("honest_gap_phrasing", "gap_phrasing", "honest_phrases"))
    if honest_phrasing:
        sections.append(
            "## Honest wording for missing or partial skills\n"
            + "\n".join(f"- {item}" for item in honest_phrasing)
        )

    ats_notes = _first_list(payload, ("ats_cleanup_notes", "ats_notes", "cleanup_notes"))
    if ats_notes:
        sections.append(
            "## ATS cleanup notes\n"
            + "\n".join(f"- {item}" for item in ats_notes)
        )

    next_step = _first_text(payload, ("next_step", "best_next_move", "recommendation"))
    if next_step:
        sections.append(f"## Best next move\n{next_step}")

    if len(sections) < 4:
        return ""

    return "\n\n".join(sections).strip()


def _analysis_markdown_is_complete(markdown: str) -> bool:
    text = str(markdown or "").lower()
    marker_groups = (
        ("verdict global", "global verdict"),
        ("points forts", "where you are a strong fit", "strong fit"),
        ("points a surveiller", "what to watch out for", "watch out"),
        ("analyse ats", "ats analysis"),
        ("prochaine etape", "next step"),
    )
    normalized = (
        text.replace("à", "a")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("ù", "u")
    )
    return sum(1 for markers in marker_groups if any(marker in normalized for marker in markers)) >= 4


def _sectioned_payload_to_markdown(payload: dict[str, Any]) -> str:
    verdict = _first_text(payload, ("verdict_global", "global_verdict", "summary", "resume", "verdict_text"))
    strengths = _first_list(payload, ("points_forts", "strengths", "strong_fit", "where_strong_fit"))
    gaps = _first_list(payload, ("points_a_surveiller", "gaps", "watch_outs", "what_to_watch_out_for"))
    ats = _first_text(payload, ("analyse_ats", "ats_analysis", "ats"))
    next_step = _first_text(payload, ("prochaine_etape", "next_step", "recommendation"))

    sections = []
    if verdict:
        sections.append(f"## 1. Global verdict\n{verdict}")
    if strengths:
        sections.append(
            "## 2. Where you are a strong fit\n"
            + "\n".join(f"- {item}" for item in strengths)
        )
    if gaps:
        sections.append(
            "## 3. What to watch out for\n"
            + "\n".join(f"- {item}" for item in gaps)
        )
    if ats:
        sections.append(f"## 4. ATS analysis\n{ats}")
    if next_step:
        sections.append(f"## 5. Next step\n{next_step}")

    if len(sections) < 4:
        return ""

    return "\n\n".join(sections).strip()


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_list(payload: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            items = []
            for item in value:
                if isinstance(item, dict):
                    title = str(item.get("title") or item.get("name") or "").strip()
                    text = str(
                        item.get("evidence")
                        or item.get("reason")
                        or item.get("description")
                        or "",
                    ).strip()
                    combined = f"**{title}** — {text}" if title and text else title or text
                    if combined:
                        items.append(combined)
                else:
                    text = str(item or "").strip()
                    if text:
                        items.append(text)
            if items:
                return items
    return []


def _ats_level_from_percent(value: Any) -> str:
    try:
        percent = float(value)
    except (TypeError, ValueError):
        return "Unknown"

    if percent >= 70:
        return "Good"
    if percent >= 40:
        return "Medium"
    return "Low"


def _resume_match_output_language(opportunity: dict[str, Any]) -> str:
    text = _language_detection_text(opportunity)
    if not text:
        return "en"

    normalized = _strip_accents(f" {text.lower()} ")
    original = f" {text.lower()} "
    french_hits = sum(1 for marker in FRENCH_OUTPUT_MARKERS if marker in normalized or marker in original)
    english_hits = sum(1 for marker in ENGLISH_OUTPUT_MARKERS if marker in normalized)
    has_french_accents = bool(re.search(r"[àâçéèêëîïôùûüÿœæ]", text.lower()))

    if has_french_accents or french_hits >= max(2, english_hits + 1):
        return "fr"
    return "en"


def _language_detection_text(opportunity: dict[str, Any]) -> str:
    parts = [
        opportunity.get("title"),
        opportunity.get("education"),
        opportunity.get("description_excerpt"),
        *_list_values(opportunity.get("skills")),
        *_list_values(opportunity.get("responsibilities")),
        *_list_values(opportunity.get("requirements")),
    ]
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def _list_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value] if value else []


def _strip_accents(value: str) -> str:
    import unicodedata

    text = str(value or "").replace("œ", "oe").replace("æ", "ae")
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _redact_contact_details(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email CV masqué]", text)
    text = re.sub(r"(?:(?:\+|00)\d{1,3}[\s.-]*)?(?:\d[\s.-]*){7,}", "[telephone CV masqué]", text)
    return text


def _resume_match_analysis_language_rule(language: str) -> str:
    if language == "fr":
        return "\n".join(
            [
                "- Write analysis_markdown and next_step entirely in French.",
                "- Use professional French suitable for a recruitment/ATS report.",
                "- Translate section labels and prose into French.",
                "- Do not leave English labels such as Global verdict, Where you are a strong fit, What to watch out for, Keywords covered, Missing keywords, or Next step.",
            ]
        )
    return "\n".join(
        [
            "- Write analysis_markdown and next_step entirely in English.",
            "- Do not use French words or phrases anywhere in analysis_markdown or next_step.",
            '- Do not use contractions. Use "do not", "it is", "cannot", "the candidate" instead of short forms.',
            "- Use plain professional English throughout.",
        ]
    )


def _resume_match_section_headings(language: str) -> tuple[str, str, str, str, str]:
    if language == "fr":
        return (
            "## 1. Verdict global",
            "## 2. Points forts",
            "## 3. Points à surveiller",
            "## 4. Analyse ATS",
            "## 5. Prochaine étape",
        )
    return (
        "## 1. Global verdict",
        "## 2. Where you are a strong fit",
        "## 3. What to watch out for",
        "## 4. ATS analysis",
        "## 5. Next step",
    )


def _resume_match_action_language_rule(language: str, *, markdown_field: str) -> str:
    if language == "fr":
        return "\n".join(
            [
                f"- Write {markdown_field} entirely in French.",
                "- Use professional French suitable for recruitment, ATS, and career coaching.",
                "- Translate all section labels, bullet labels, explanations, and next steps into French.",
                "- Keep JSON field names unchanged.",
                "- Do not invent experience, tools, certifications, or achievements.",
            ]
        )
    return "\n".join(
        [
            f"- Write {markdown_field} entirely in English.",
            f"- Do not use French words or phrases anywhere in {markdown_field}.",
            '- Do not use contractions. Use "do not", "it is", "cannot", "the candidate" instead of short forms.',
            "- Use plain professional English throughout.",
            "- Keep JSON field names unchanged.",
        ]
    )


def _resume_cv_summary_style_rule(language: str) -> str:
    if language == "fr":
        return "\n".join(
            [
                "CV SUMMARY STYLE RULE:",
                "- Write CV titles and summaries as direct resume text ready to paste into the CV.",
                "- Do not use the candidate name in CV titles or summaries.",
                '- Do not write in third person, for example "Hiba Belghith possede..." or "Elle maitrise...".',
                '- Do not use first-person pronouns either, for example "je", "mon", "ma", or "mes", unless explicitly requested.',
                "- Preferred French CV style: no pronoun, role-first phrase, for example \"Comptable junior avec 2 ans d'experience en cabinet, specialisee en saisie comptable...\".",
            ]
        )
    return "\n".join(
        [
            "CV SUMMARY STYLE RULE:",
            "- Write CV titles and summaries as direct resume text ready to paste into the resume.",
            "- Do not use the candidate name in resume titles or summaries.",
            '- Do not write in third person, for example "The candidate has..." or "She is...".',
            '- Do not use first-person pronouns either, for example "I", "my", or "me", unless explicitly requested.',
            '- Preferred resume style: no pronoun, role-first phrase, for example "Junior Accountant with 2 years of experience in accounting firms...".',
        ]
    )


def _resume_optimization_section_headings(language: str) -> tuple[str, str, str, str, str, str, str]:
    if language == "fr":
        return (
            "## Titre de profil proposé",
            "## Résumé professionnel optimisé",
            "## Section compétences à renforcer",
            "## Expériences à reformuler pour cette offre",
            "## Formulations honnêtes pour les compétences partielles",
            "## Notes de nettoyage ATS",
            "## Meilleure prochaine action",
        )
    return (
        "## Updated headline",
        "## Updated summary",
        "## Updated core skills section",
        "## Resume bullets to strengthen this application",
        "## Honest wording for missing or partial skills",
        "## ATS cleanup notes",
        "## Best next move",
    )


def _resume_summary_section_headings(language: str) -> tuple[str, str, str, str]:
    if language == "fr":
        return (
            "## Résumé professionnel recommandé",
            "## Version plus prudente",
            "## Mots-clés ATS à inclure",
            "## Mots à éviter",
        )
    return (
        "## Recommended professional summary",
        "## More cautious version",
        "## ATS keywords to include",
        "## Words to avoid",
    )


def _resume_interview_section_headings(language: str) -> tuple[str, str, str, str, str]:
    if language == "fr":
        return (
            "## 1. Questions techniques - basées sur vos écarts",
            "## 2. Questions comportementales - basées sur le poste",
            "## 3. Questions à poser au recruteur",
            "## 4. Points sensibles à préparer",
            "## 5. Conseil de préparation en une phrase",
        )
    return (
        "## 1. Technical questions - based on your gaps",
        "## 2. Behavioral questions - based on the role",
        "## 3. Questions to ask the interviewer",
        "## 4. Red flags to prepare for",
        "## 5. One-line preparation tip",
    )


def _resume_interview_format_labels(language: str) -> dict[str, str]:
    if language == "fr":
        return {
            "technical_label": "Compétence technique évaluée",
            "behavioral_label": "Compétence comportementale évaluée",
            "red_flag_label": "Point sensible potentiel",
            "question": "Question",
            "why": "Pourquoi cette question",
            "answer": "Comment répondre honnêtement",
            "star": "Indice STAR",
            "strategy": "Stratégie de réponse",
        }
    return {
        "technical_label": "Technology or skill being tested",
        "behavioral_label": "Behavioral skill being tested",
        "red_flag_label": "Potential red flag",
        "question": "Question",
        "why": "Why this question",
        "answer": "How to answer honestly",
        "star": "STAR hint",
        "strategy": "Response strategy",
    }


def _resume_cover_letter_section_headings(language: str) -> tuple[str, str, str]:
    if language == "fr":
        return (
            "## Lettre de motivation",
            "## Version courte pour candidature en ligne",
            "## Notes de personnalisation",
        )
    return (
        "## Cover Letter",
        "## Short version for online applications",
        "## Personalization notes",
    )


def _force_ats_level_in_markdown(markdown: str, ats_level: str) -> str:
    if not ats_level or ats_level in {"Inconnu", "Unknown"}:
        return markdown

    pattern = re.compile(
        r"((?:Niveau compatibilit[eé] ATS|ATS compatibility level)\s*:\s*)"
        r"(Bon|Moyen|Faible|Inconnu|Good|Medium|Low|Unknown)",
        re.IGNORECASE,
    )
    if pattern.search(markdown):
        def replace(match):
            prefix = match.group(1)
            if "niveau" in prefix.lower():
                localized = {
                    "Good": "Bon",
                    "Medium": "Moyen",
                    "Low": "Faible",
                    "Unknown": "Inconnu",
                }.get(ats_level, ats_level)
                return f"{prefix}{localized}"
            return f"{prefix}{ats_level}"

        return pattern.sub(replace, markdown, count=1)

    return markdown


def _force_ats_score_in_markdown(markdown: str, ats_percent: Any) -> str:
    try:
        normalized_percent = int(round(float(ats_percent)))
    except (TypeError, ValueError):
        return markdown

    pattern = re.compile(
        r"((?:(?:BidWise\s+)?ATS\s+Score|Score\s+ATS\s+BidWise)\s*:\s*)\d+(?:\.\d+)?%",
        re.IGNORECASE,
    )
    return pattern.sub(rf"\g<1>{normalized_percent}%", markdown)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    if value in (None, ""):
        return "not visible in resume"
    text = str(value).strip()
    return text or "not visible in resume"


def _list(value: Any) -> str:
    if value in (None, ""):
        return "not visible in resume"
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item or "").strip()]
    else:
        items = [str(value).strip()]
    if not items:
        return "not visible in resume"
    return ", ".join(items)


def _list_raw(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item or "").strip()]


def _nested(value: dict[str, Any], *keys: str) -> str:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return "not visible in resume"
        current = current.get(key)
    return _text(current)
