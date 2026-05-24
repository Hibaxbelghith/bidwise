# JobBERT Recommendation Pipeline

BidWise uses a hybrid recommendation engine: deterministic business constraints keep results safe, while JobBERT provides the main semantic job-match signal.

## Purpose

The goal is not to match a fixed Python list of skills. The system converts every opportunity into a compact semantic document, embeds it with `TechWolf/JobBERT-v3`, and compares it with the candidate profile. This lets the engine understand roles and descriptions even when sources use different languages, wording, or incomplete structured skills.

## Opportunity Text Preparation

Before JobBERT embedding, `prepare_combined_text()` builds a structured text payload from the canonical opportunity:

- opportunity type and source
- role/title, organization, sector, and location
- contract, work mode, schedule, experience, education, salary
- source skills, raw skills, ESCO-normalized skills, and languages
- selected description signals from mission, profile, requirements, skills, stack, responsibilities, and similar sections

This is intentionally source-agnostic. Keejob, LinkedIn, EmploiTunisie, MarchesPublics, and future sources are all reduced into the same semantic format. Job-specific fields are included when available, but project, funding, research, and tender-like opportunities still keep their type, source, object, sector, location, and description requirements.

## Optional LLM Field Extraction

For rich unstructured descriptions, BidWise can run an offline LLM enrichment step before JobBERT. This is designed for Ollama/local models or a cloud LLM when available. It must not run during the `For You` page request.

The LLM extracts matching fields into `extra_data.llm_enrichment`:

- canonical role and target roles
- skills, tools, and professional domains
- seniority and years of experience
- contract types and work modes
- locations, salary, and education level
- responsibilities and requirements
- short evidence phrases
- optional coarse business families with `family_confidence`

When those fields exist, `prepare_combined_text()` injects them into the semantic document passed to JobBERT. This gives JobBERT a clearer representation than the raw scraped paragraph while keeping ranking fast at request time.

The LLM is an extractor, not the ranking engine. JobBERT remains responsible for semantic profile-opportunity matching, ESCO remains responsible for skill normalization, and product rules still control hard constraints such as seniority gaps, location, and contract mismatch.

Business families are intentionally secondary. They are used only as a coarse guardrail when the LLM extraction is confident. If `family_confidence` is low or the family is `other`, ranking relies on the extracted role, domains, skills, responsibilities, requirements, and the JobBERT semantic score. This avoids turning the system into a brittle static classifier.

## Why Description Signals Matter

Some sources provide almost no structured skills. Others provide skills that are incomplete or extracted by older heuristics. Keejob often has rich descriptions, so the pipeline now keeps mission/profile/skills sections instead of compressing the text to a tiny title-like snippet.

The section selector is lightweight and deterministic for performance. It does not call Gemini or Ollama. Its job is only to prepare high-quality text for JobBERT; the semantic judgment comes from the model embedding.

## Role of JobBERT

JobBERT produces normalized vectors for:

- the user profile
- every prepared opportunity text

The recommendation service computes cosine similarity between these vectors. This score is used internally to boost semantically close opportunities, cap weak/noisy matches, and separate strong recommendations from lower-confidence opportunities.

The UI does not show a separate JobBERT percentage because users need one clear match score. JobBERT is part of that final score.

## Role of ESCO

ESCO is used for normalization and explainability:

- maps source skills to standardized skill concepts when possible
- improves structured skill evidence
- supports future analytics by skill coverage and skill families

ESCO is not the only ranking mechanism. It complements JobBERT, especially when source skills are present and reliable.

## Performance Rules

- Embeddings are generated offline or in batches, not during normal page rendering.
- The prepared text is capped to `JOBBERT_MAX_TEXT_CHARS` to keep inference fast.
- Existing vectors are reused unless commands run with `--force`.
- The recommendation request uses precomputed opportunity vectors whenever available.

## Rollback

The hybrid JobBERT signal can be disabled without deleting data:

```env
JOBBERT_RERANK_ENABLED=false
JOBBERT_ALLOW_LIVE_FALLBACK=false
```

Restart the backend after changing these values.
