# AI Recommendation Final Validation

This document is the final validation checklist for the BidWise AI recommendation system.

## Validated Architecture

- JobBERT provides semantic profile-to-opportunity matching.
- Business scoring adds role, skills, location, work mode, and experience evidence.
- Hierarchy rules detect seniority, qualification, and responsibility gaps.
- Ollama is used only for `needs_llm=true` hierarchy ambiguity, not for all scraped opportunities.
- LLM output is guarded by deterministic policy:
  - low confidence remains reviewable;
  - contradictory JSON is normalized to `unclear`;
  - exact role + strong skill evidence can override a weak LLM concern;
  - LLM rejection is applied only when supported by explicit opportunity terms.

## Final Benchmark Command

```powershell
docker compose run --rm -e LLM_ENRICHMENT_ENABLED=true -e LLM_PROVIDER=ollama -e OLLAMA_MODEL=llama3.2:3b -e OLLAMA_TIMEOUT_SECONDS=180 backend python manage.py benchmark_final_recommendation_profiles --use-llm-validation --profiles comptable_junior,production_team_lead,civil_engineer_junior,it_helpdesk --candidate-limit 1700 --rerank-candidates 120 --top 15 --output-json backend/benchmark_reports/final_ai_recommendation_validation.json --json
```

## Acceptance Criteria

- `llm_errors` is `0`.
- Exact matches remain `STRONG_MATCH`, especially:
  - `Comptable Junior` / relevant accountant roles for `comptable_junior`;
  - `Chef d'équipe production` for `production_team_lead`;
  - `Ingénieur en Génie Civil (Travaux)` for `civil_engineer_junior`;
  - `IT Helpdesk Officer` for `it_helpdesk`.
- Senior, manager, responsable, or clearly overqualified/underqualified roles remain `RELATED_REVIEW`.
- `needs_llm` is low and controlled after validation.
- Rows where the LLM was overridden by strong deterministic evidence expose:
  - `llm_overridden_by_exact_evidence: true`;
  - `llm_hierarchy_policy.reason`.

## Interpretation

The final system should be described as a hybrid recommendation engine:

1. semantic retrieval and scoring produce the candidate ranking;
2. business and hierarchy rules protect recommendation quality;
3. local LLM validation is used only as a bounded reviewer for ambiguous hierarchy cases;
4. deterministic evidence remains authoritative when it is stronger than a weak or over-strict LLM judgment.

## Production Decision

Do not run Ollama on every scraped opportunity.

Production integration should be limited to top recommendations where:

- `hierarchy_validation.needs_llm` is true;
- deterministic evidence is insufficient to decide safely;
- a cache exists for profile/opportunity hierarchy decisions;
- timeout and fallback keep the recommendation flow usable.
