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
    expected_ats_level = _ats_level_from_percent(
        _dict(match.get("ats")).get("keyword_coverage_percent"),
    )

    try:
        payload = llm_provider.generate_json(prompt, schema=RESUME_MATCH_ANALYSIS_SCHEMA)
    except (LLMProviderUnavailable, LLMTransientProviderError, LLMProviderError) as exc:
        logger.warning("Resume match LLM analysis failed provider=%s reason=%s", getattr(llm_provider, "provider_name", ""), exc)
        raise ResumeMatchLLMError(str(exc)) from exc

    return _normalize_analysis_payload(payload, provider=llm_provider, expected_ats_level=expected_ats_level)


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

    # Keep the LLM grounded with neutral signals only. Do not pass generated
    # reason strings or pre-computed bullets here, otherwise the model tends to
    # copy generic labels instead of writing a role-specific analysis.
    # NOTE: All instructions and examples are in English to prevent the LLM from
    # generating French prose with apostrophes that break JSON parsing.
    return f"""
You are BidWise AI, a senior recruitment and ATS (Applicant Tracking System) expert.

ABSOLUTE RULE: Use ONLY the structured data provided below.
Never invent experience, certifications, tools, or achievements.
If information is missing, write "not visible in resume".

LANGUAGE RULE:
- Write the entire Markdown output in English only.
- Do not use French words or phrases anywhere in the output.
- Do not use contractions. Use "do not", "it is", "cannot", "the candidate" instead of short forms.
- Use plain professional English throughout.

==================================================
CANDIDATE DATA
==================================================
Target role: {_list(profile.get("target_roles"))}
Level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Profile skills: {_list(profile.get("skills"))}
Preferred locations: {_list(profile.get("locations"))}
Contract types sought: {_list(profile.get("employment_types"))}

Resume signals detected:
- Canonical role in resume: {_text(resume.get("canonical_role"))}
- Skills in resume: {_list(resume.get("skills"))}
- Tools in resume: {_list(resume.get("tools"))}
- Domains in resume: {_list(resume.get("domains"))}
- Resume excerpt: {_text(resume.get("summary_excerpt"))}

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
- The ats_level field and the "ATS compatibility level" line must follow this rule.

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

## 1. Global verdict
2 to 3 direct sentences.
Start with "Your resume shows ..."
State clearly whether this is a strong match, partial match, or weak match.

## 2. Where you are a strong fit
Bullet points only.
Each bullet: short bold title + concrete explanation tied to the job posting.
Minimum 2 bullets, maximum 4.
Do NOT use generic titles such as "Role alignment", "Relevant keywords", or "Experience fit".
Each bullet must name a real skill, tool, domain, or concrete signal from the resume.
Good example:
- **Python and Apache Spark** - Resume shows these technologies, directly aligned with the ETL pipeline requirements in the job posting.
Bad example:
- **Role alignment** - Role evidence overlaps with the opportunity.

## 3. What to watch out for
Bullet points only.
Each bullet: short bold title + detailed gap explanation + impact on the application.
Cover at least 2 critical gaps first, then 1 useful gap if available.
Prioritize specific technologies (tools, platforms, languages, frameworks) over generic skills.
For each gap, explain: what the job requires, what the resume shows instead, and the ATS or recruiter impact.
Good example:
- **Azure Databricks not mentioned** - The job lists Databricks as a required skill for PySpark/SQL pipelines. Its absence lowers the ATS score and may trigger an automatic filter.
Bad example:
- **API not mentioned** - The job requires API.

## 4. ATS analysis
- BidWise ATS Score: {_text(ats.get("keyword_coverage_percent"))}%
- Keywords covered: list the matched keywords
- Missing keywords: critical gaps first, then useful gaps
- ATS compatibility level: apply the ABSOLUTE ATS RULE above + one sentence explanation

## 5. Next step
One concrete and specific action to take before applying.
Start with an action verb.
Cover the 2 or 3 most critical gaps, not a single isolated keyword.
Good example:
Add a Technical Skills section to your resume listing Azure Databricks, PySpark/SQL, and IBM DataStage, noting your level of exposure to each tool.

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

    return f"""
You are BidWise AI, a senior recruitment and ATS (Applicant Tracking System) expert
specializing in CV optimization.

Your task: produce concrete CV optimization suggestions tailored to this job posting.

ABSOLUTE RULES:
- Use only the structured data provided below.
- Never invent experience, certifications, tools, degrees, or achievements.
- For any critical technology absent from the resume, suggest honest wording only:
  "exposure", "basic knowledge", "personal project", or "academic project" -
  only if the provided data supports it. Otherwise write "add only if true".
- All suggestions must be directly copy-pasteable into a CV.
- ATS format: plain text, no tables, no icons, no complex layout.
- Do not rewrite the entire CV. Suggest only the sections that need improvement.
- Maximum 700 words total.

LANGUAGE RULE:
- Write the entire Markdown output in English only.
- Do not use French words or phrases anywhere in the output.
- Do not use contractions. Use "do not", "it is", "cannot", "the candidate" instead of short forms.
- Use plain professional English throughout.

==================================================
CANDIDATE DATA
==================================================
Target role: {_list(profile.get("target_roles"))}
Level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Profile skills: {_list(profile.get("skills"))}
Preferred locations: {_list(profile.get("locations"))}
Contract types sought: {_list(profile.get("employment_types"))}

Resume signals:
- Canonical role: {_text(resume.get("canonical_role"))}
- Skills: {_list(resume.get("skills"))}
- Tools: {_list(resume.get("tools"))}
- Domains: {_list(resume.get("domains"))}
- Resume excerpt: {_text(resume.get("summary_excerpt"))}

==================================================
JOB OPPORTUNITY DATA
==================================================
Title: {_text(opportunity.get("title"))}
Company: {_text(opportunity.get("company"))}
Location: {_text(opportunity.get("location"))}
Contract: {_text(opportunity.get("contract"))}
Experience required: {_nested(opportunity, "experience", "min")} - {_nested(opportunity, "experience", "max")} years
Required skills: {_list(opportunity.get("skills"))}
Responsibilities: {_list(opportunity.get("responsibilities"))}
Requirements: {_list(opportunity.get("requirements"))}
Description excerpt: {_text(opportunity.get("description_excerpt"))}

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

## Updated headline
Give exactly 2 CV title options.
- Option 1: strong version based on skills visible in the resume.
- Option 2: cautious version if critical gaps cannot be proven.

## Updated summary
3 to 5 professional lines.
Highlight the strongest evidence from the resume.
Include job keywords only if they are visible in the resume or honestly qualifiable.

## Updated core skills section
4 to 6 skill lines.
Style example: "Data Engineering: ETL/ELT pipelines, SQL, data quality"
Do not list any technology as mastered if it is absent from the resume.

## Resume bullets to strengthen this application
4 to 6 experience bullets.
Each bullet starts with an action verb.
Each bullet must be defensible from the resume data or framed as a conditional suggestion.
If a bullet depends on unproven experience, start with: "If applicable:"

## Honest wording for missing or partial skills
2 to 4 honest phrasings for critical or useful gaps.
Goal: help the candidate pass ATS filters without misrepresenting their background.
Example: "Exposure to Azure Databricks through academic project" - only if compatible with the data.

## ATS cleanup notes
3 to 5 short tips to make the CV more ATS-friendly.
Include guidance on keyword placement in the top third of the CV.

## Best next move
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

    return f"""
You are BidWise AI, a senior recruiter and ATS resume optimization expert.

Your task: rewrite the professional summary for this resume and job opportunity.

ABSOLUTE RULES:
- Use only the structured evidence below.
- Never invent experience, certifications, tools, achievements, or years of experience.
- If a skill is missing, do not claim mastery. Use honest wording such as "exposure to" only if supported.
- Write in English only.
- Do not use contractions.
- Make the summaries ATS-friendly, recruiter-friendly, and directly copy-pasteable.
- Maximum 450 words total.

==================================================
CANDIDATE DATA
==================================================
Target role: {_list(profile.get("target_roles"))}
Level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Profile skills: {_list(profile.get("skills"))}

Resume signals:
- Canonical role: {_text(resume.get("canonical_role"))}
- Skills: {_list(resume.get("skills"))}
- Tools: {_list(resume.get("tools"))}
- Domains: {_list(resume.get("domains"))}
- Current resume excerpt: {_text(resume.get("summary_excerpt"))}

==================================================
JOB OPPORTUNITY DATA
==================================================
Title: {_text(opportunity.get("title"))}
Company: {_text(opportunity.get("company"))}
Required skills: {_list(opportunity.get("skills"))}
Responsibilities: {_list(opportunity.get("responsibilities"))}
Requirements: {_list(opportunity.get("requirements"))}
Description excerpt: {_text(opportunity.get("description_excerpt"))}

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

## Recommended professional summary
Write one polished 3 to 4 line summary tailored to the job.

## More cautious version
Write one honest version for cases where some job keywords are not strongly proven in the resume.

## ATS keywords to include
List 5 to 8 keywords that are safe to include based on the resume evidence.

## Words to avoid
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

    return f"""
You are BidWise AI, a senior HR interview coach with 15 years of experience
in technical and behavioral interviews.

ABSOLUTE RULE: Use ONLY the structured data provided.
Never invent experience, certifications, tools, or achievements.
Every question must be grounded in a real gap or signal from the evidence.

LANGUAGE RULE:
- Write the entire output in English only.
- Do not use contractions.
- Use direct, professional tone.

==================================================
CANDIDATE DATA
==================================================
Target role: {_list(profile.get("target_roles"))}
Level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Resume skills: {_list(resume.get("skills"))}
Resume tools: {_list(resume.get("tools"))}
Resume domains: {_list(resume.get("domains"))}
Resume excerpt: {_text(resume.get("summary_excerpt"))}

==================================================
JOB OPPORTUNITY DATA
==================================================
Title: {_text(opportunity.get("title"))}
Company: {_text(opportunity.get("company"))}
Required skills: {_list(opportunity.get("skills"))}
Responsibilities: {_list(opportunity.get("responsibilities"))}
Requirements: {_list(opportunity.get("requirements"))}
Description excerpt: {_text(opportunity.get("description_excerpt"))}

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

## 1. Technical questions - based on your gaps
Generate 2 questions the interviewer will likely ask about the critical gaps.
For each question:
- Bold title: the technology or skill being tested
- The exact question
- Why this question: which gap it targets, in one sentence
- How to answer honestly: one short answer strategy

## 2. Behavioral questions - based on the role
Generate 2 questions about soft skills and work style relevant to this role.
Each question must reference a specific responsibility from the job posting.
Format: question + STAR method hint (Situation, Task, Action, Result).

## 3. Questions to ask the interviewer
Generate 2 smart questions the candidate should ask to show genuine interest
and technical depth. Based only on the job description and company data.

## 4. Red flags to prepare for
List 2 potential red flags the recruiter may raise based on the gaps,
with a short honest response strategy for each.

## 5. One-line preparation tip
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

    # Keywords that MUST appear at least once in the letter body
    must_include = matched[:6] + critical[:3]
    # Keywords that SHOULD appear if a natural sentence allows it
    should_include = useful[:3]

    job_title_exact = _text(opportunity.get("title"))

    return f"""
You are BidWise AI, a senior recruiter and ATS-optimized cover letter specialist.

Your task: write a tailored, ATS-strong motivation letter for this job opportunity.

ABSOLUTE RULES:
- Use only the structured evidence below.
- Never invent employment history, certifications, achievements, tools, salary, or personal details.
- If name, email, phone, portfolio, or date are not visible, use placeholders.
- If a skill is absent from the resume, do not claim mastery. Use honest framing instead.
- Write in English only. No contractions.
- Maximum 600 words total across both letter versions combined.

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
   "I am currently deepening my knowledge of [gap keyword] and look forward to
   applying it in this role." Only use this for gaps listed as critical.
   Critical gaps: {_list(critical[:3])}

5. ACTION VERB RULE: Every paragraph must start with or contain a strong action verb
   in the first sentence. Use: Built, Designed, Delivered, Led, Developed, Automated,
   Implemented, Maintained, Optimized, Collaborated.

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

==================================================
CANDIDATE DATA
==================================================
Target role: {_list(profile.get("target_roles"))}
Level: {_text(profile.get("experience_level"))} - {_text(profile.get("experience_years"))} years
Skills: {_list(profile.get("skills"))}
Locations: {_list(profile.get("locations"))}

Resume signals:
- Canonical role: {_text(resume.get("canonical_role"))}
- Skills: {_list(resume.get("skills"))}
- Tools: {_list(resume.get("tools"))}
- Domains: {_list(resume.get("domains"))}
- Resume excerpt: {_text(resume.get("summary_excerpt"))}

==================================================
JOB OPPORTUNITY DATA
==================================================
Title: {job_title_exact}
Company: {_text(opportunity.get("company"))}
Location: {_text(opportunity.get("location"))}
Contract: {_text(opportunity.get("contract"))}
Experience required: {_nested(opportunity, "experience", "min")} - {_nested(opportunity, "experience", "max")} years
Required skills: {_list(opportunity.get("skills"))}
Responsibilities: {_list(opportunity.get("responsibilities"))}
Requirements: {_list(opportunity.get("requirements"))}
Description excerpt: {_text(opportunity.get("description_excerpt"))}

==================================================
EXPECTED OUTPUT
==================================================
Return only a valid JSON object with fields: cover_letter_markdown and next_step.

## Cover Letter
[Candidate Full Name]
[City / Country]
[Email] | [Phone] | [Portfolio or GitHub link]
[Date]

Hiring Team
{_text(opportunity.get("company"))}

Dear Hiring Team,

Paragraph 1: State the exact role title and company. Express clear interest. One or two sentences.
Paragraph 2: Connect the 2 or 3 strongest resume skills to the core job requirements. Name tools. Start with an action verb.
Paragraph 3: Describe relevant projects, domains, or responsibilities from the resume. Be specific. Start with an action verb.
Paragraph 4: Address the company or role specifically using only the job data. What makes this opportunity relevant.
Paragraph 5: If critical gaps exist, address them honestly using the GAP FRAMING RULE. Otherwise use for a second strength point.
Paragraph 6: Close with a professional call to action. Invite a conversation about the application.

Sincerely,
[Candidate Full Name]

## Short version for online applications
3 paragraphs. Must contain the exact job title and at least 3 keywords from the MUST INCLUDE list.
Paragraph 1: Role, company, and strongest match signal.
Paragraph 2: Two or three concrete skills or tools from the resume tied to job requirements.
Paragraph 3: Motivation and call to action.

## Personalization notes
3 short bullets: what placeholders or unverifiable facts the candidate must check before sending.

The next_step field: the single most impactful keyword or fact the candidate should add before sending.
""".strip()



def _normalize_analysis_payload(
    payload: dict[str, Any],
    *,
    provider: LLMProvider,
    expected_ats_level: str,
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
            return value.strip()

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
            return value.strip()
    return ""


def _extract_cover_letter_markdown(payload: dict[str, Any]) -> str:
    for key in ("cover_letter_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_interview_markdown(payload: dict[str, Any]) -> str:
    for key in ("interview_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _extract_optimization_markdown(payload: dict[str, Any]) -> str:
    for key in ("optimization_markdown", "analysis_markdown", "markdown", "content", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

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


def _force_ats_level_in_markdown(markdown: str, ats_level: str) -> str:
    if not ats_level or ats_level in {"Inconnu", "Unknown"}:
        return markdown

    pattern = re.compile(
        r"((?:Niveau compatibilit[eé] ATS|ATS compatibility level)\s*:\s*)"
        r"(Bon|Moyen|Faible|Inconnu|Good|Medium|Low|Unknown)",
        re.IGNORECASE,
    )
    if pattern.search(markdown):
        return pattern.sub(rf"\1{ats_level}", markdown, count=1)

    return markdown


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    if value in (None, ""):
        return "non visible dans le CV"
    text = str(value).strip()
    return text or "non visible dans le CV"


def _list(value: Any) -> str:
    if value in (None, ""):
        return "non visible dans le CV"
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item or "").strip()]
    else:
        items = [str(value).strip()]
    if not items:
        return "non visible dans le CV"
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
            return "non visible dans le CV"
        current = current.get(key)
    return _text(current)
