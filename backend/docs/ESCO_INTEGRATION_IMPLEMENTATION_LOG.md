# ESCO Integration Implementation Log

Last updated: 2026-05-15

This document records the BidWise ESCO integration work from the first architecture audit through the current production-safe normalization pipeline, backfills, coverage reporting, and recommendation-safe enrichment.

It is intentionally operational:
- what was built
- why it was built
- which files were involved
- which commands were used
- which problems were found
- what remains to do next

## 1. Executive summary

BidWise did **not** move directly from raw skills to a redesigned ESCO-based recommender.

The work was intentionally split into safe phases:

1. Audit the existing recommendation and skill pipelines.
2. Build ESCO storage infrastructure.
3. Replace the temporary 43-skill prototype with the official local ESCO catalog.
4. Build `normalize_skills_to_esco()` as an isolated service.
5. Store normalized skills in parallel with raw skills.
6. Add a small conservative recommendation enrichment based on stored normalized overlap.
7. Audit why real normalized fields stayed empty.
8. Repair the missing execution paths and backfill historical data.
9. Improve CV candidate quality filtering and add resume cleanup mode.

The current system is now in a much healthier state:

- ESCO catalog is stored locally and queryable.
- Skills are normalized conservatively and safely.
- Raw skills are preserved everywhere.
- Historical opportunities, profiles, and resumes have been backfilled.
- Recommendation logic remains stable and only lightly enriched.
- Coverage and failure reporting exist.
- BidWise custom alias infrastructure is now available for review-approved coverage expansion.

## 2. Initial problem statement

Before this work, BidWise had:

- a stable recommendation engine
- semantic retrieval + pgvector + CrossEncoder
- several raw skill sources
- fragmented normalization logic
- no reliable canonical multilingual skill layer

The central risk was:

- duplicate normalization
- incompatible skill representations
- broken embeddings
- recommendation instability

The first decision was therefore:

> integrate ESCO progressively, starting with infrastructure and storage, not recommendation redesign.

## 3. Phase-by-phase implementation history

### Phase 0. Architecture audit

Goal:
- trace where skills enter, are extracted, stored, embedded, and scored

Key findings:
- opportunity skills came from scraper payloads plus NLP enrichment
- profile skills came from manual profile fields and resume semantic extraction
- embeddings and recommendation scoring did **not** directly use ESCO
- normalization logic was fragmented
- `Opportunite.skills`, `Profil.competences`, and `ProfileResume.extracted_skills` were the main legacy fields

Key files audited:
- [backend/opportunities/tasks.py](/d:/Documents/BidWise/backend/opportunities/tasks.py)
- [backend/opportunities/processing.py](/d:/Documents/BidWise/backend/opportunities/processing.py)
- [backend/opportunities/materialization/service.py](/d:/Documents/BidWise/backend/opportunities/materialization/service.py)
- [backend/users/serializers.py](/d:/Documents/BidWise/backend/users/serializers.py)
- [backend/users/tasks.py](/d:/Documents/BidWise/backend/users/tasks.py)
- [backend/users/resume_semantic/service.py](/d:/Documents/BidWise/backend/users/resume_semantic/service.py)
- [backend/ai/recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py)
- [backend/ai/retrieval.py](/d:/Documents/BidWise/backend/ai/retrieval.py)

### Phase 1. Temporary ESCO infrastructure prototype

Goal:
- validate ESCO storage, vector indexing, and cache behavior before touching the main pipelines

Implemented:
- `ESCOSkill` model
- loader for a curated subset of skills
- ESCO skill embeddings
- lazy cached in-memory index

Key files:
- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)
- [backend/ai/management/commands/generate_esco_skill_embeddings.py](/d:/Documents/BidWise/backend/ai/management/commands/generate_esco_skill_embeddings.py)

Important lesson from this phase:
- the 43-skill seed was good enough for validating infrastructure
- it was **not** acceptable as a production normalization vocabulary

### Phase 2. Vector metadata and safety hardening

Goal:
- make the ESCO vector index self-describing and safe across future embedding-space changes

Implemented on `ESCOSkill`:
- `embedding_model`
- `embedding_dimensions`
- `embedding_version`
- `embedding_updated_at`

Added helpers:
- [backend/ai/esco_skill_embeddings.py](/d:/Documents/BidWise/backend/ai/esco_skill_embeddings.py)

Why this mattered:
- BidWise recommendation embeddings are currently `384`-dimensional
- resume semantic mapping may use `BAAI/bge-m3`
- future normalization code must never compare incompatible vector spaces

### Phase 3. Official ESCO catalog ingestion

Goal:
- replace the temporary seed with the official local multilingual ESCO catalog

Implemented:
- import of official EN + FR CSV files
- URI-based EN/FR merge
- clean internal occupation-skill tables
- idempotent bulk ingestion

Key files:
- [backend/ai/esco_catalog_ingestion.py](/d:/Documents/BidWise/backend/ai/esco_catalog_ingestion.py)
- [backend/ai/management/commands/import_esco_catalog.py](/d:/Documents/BidWise/backend/ai/management/commands/import_esco_catalog.py)
- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)

Main imported structures:
- `ESCOSkill`
- `ESCOOccupationCatalog`
- `ESCOOccupationSkillRelation`

Key design choice:
- keep `ESCOOccupation` used by the old mapper isolated
- import the official catalog into dedicated internal tables

### Phase 4. Production-grade normalization service

Goal:
- build `normalize_skills_to_esco()` as an isolated, deterministic, conservative service

Implemented:
- exact preferred-label matching
- exact alt-label and hidden-label matching
- semantic fallback only after exact failure
- embedding compatibility checks
- conservative false-positive guards

Key files:
- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)
- [backend/ai/esco_skill_storage.py](/d:/Documents/BidWise/backend/ai/esco_skill_storage.py)

Important safety rules:
- no FAISS
- no Redis dependency
- no runtime DB scans
- no recommendation coupling

### Phase 5. Storage integration into real pipelines

Goal:
- normalize skills during ingestion/storage only
- keep raw and normalized data in parallel

Implemented fields:

On `Opportunite`:
- `raw_skills`
- `normalized_skills`
- `skills_normalization_hash`
- `skills_normalization_updated_at`
- `skills_normalization_error`

On `Profil`:
- `raw_skills`
- `normalized_skills`
- `skills_normalization_hash`
- `skills_normalization_updated_at`
- `skills_normalization_error`

On `ProfileResume`:
- `extracted_raw_skills`
- `extracted_normalized_skills`
- `extracted_skills_normalization_hash`
- `extracted_skills_normalization_updated_at`
- `extracted_skills_normalization_error`

Key files:
- [backend/opportunities/models.py](/d:/Documents/BidWise/backend/opportunities/models.py)
- [backend/users/models.py](/d:/Documents/BidWise/backend/users/models.py)
- [backend/ai/tasks.py](/d:/Documents/BidWise/backend/ai/tasks.py)
- [backend/ai/esco_skill_storage.py](/d:/Documents/BidWise/backend/ai/esco_skill_storage.py)
- [backend/opportunities/processing.py](/d:/Documents/BidWise/backend/opportunities/processing.py)
- [backend/opportunities/materialization/service.py](/d:/Documents/BidWise/backend/opportunities/materialization/service.py)
- [backend/users/serializers.py](/d:/Documents/BidWise/backend/users/serializers.py)
- [backend/users/resume_semantic/service.py](/d:/Documents/BidWise/backend/users/resume_semantic/service.py)

Design principle:
- normalized ESCO data is additive
- raw data is never overwritten

### Phase 6. First conservative recommendation enrichment

Goal:
- let stored normalized skills participate slightly in recommendation ranking without redesigning the recommender

Implemented:
- small normalized-overlap bonus
- low impact
- capped
- exact canonical overlap only
- no runtime normalization

Key files:
- [backend/ai/esco_recommendation_signals.py](/d:/Documents/BidWise/backend/ai/esco_recommendation_signals.py)
- [backend/ai/recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py)
- [backend/ai/user_features.py](/d:/Documents/BidWise/backend/ai/user_features.py)
- [backend/ai/retrieval.py](/d:/Documents/BidWise/backend/ai/retrieval.py)

Feature flag:
- `RECOMMENDATION_ENABLE_NORMALIZED_SKILL_BONUS`

Intent:
- confidence enrichment only
- not a scoring rewrite

Exact pipeline position:
1. pgvector / semantic retrieval selects the shortlist
2. `rank_opportunities()` computes semantic score plus business score
3. the normalized ESCO overlap bonus is applied inside `_business_score()`
4. the pre-rerank final score is produced
5. CrossEncoder reranking runs on that shortlist afterwards
6. quality gates and fallback logic apply after reranking

Relevant files:
- [backend/ai/views.py](/d:/Documents/BidWise/backend/ai/views.py)
- [backend/ai/retrieval.py](/d:/Documents/BidWise/backend/ai/retrieval.py)
- [backend/ai/recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py)
- [backend/ai/crossencoder/service.py](/d:/Documents/BidWise/backend/ai/crossencoder/service.py)

This means the current ESCO enrichment already sits in the safest first recommendation slot:
- after retrieval
- before CrossEncoder reranking
- without touching embeddings or candidate generation

### Phase 7. Experience-gap credibility calibration

Goal:
- reduce obviously senior recommendations for junior/internship profiles without hard filtering

Implemented:
- soft experience-gap penalty
- explainable, capped, reversible

Key file:
- [backend/ai/recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py)

Feature flag:
- `RECOMMENDATION_ENABLE_EXPERIENCE_GAP_PENALTY`

This phase was not strictly ESCO infrastructure, but it was added after real recommendation credibility testing.

### Phase 8. Production audit of missing normalized data

Problem discovered:

Even though the recommendation engine already supported normalized fields, almost all real rows had empty ESCO payloads.

Observed state before repair:
- opportunities total around `2960`
- opportunities with `normalized_skills` around `6`
- profiles with `normalized_skills` around `0`
- resumes with `extracted_normalized_skills` around `0`

This meant:
- ESCO existed technically
- but barely participated in real recommendations

### Phase 9. Root-cause repair and backfill

Goal:
- identify exactly why normalized fields stayed empty
- repair only the broken execution paths
- backfill historical rows safely

Root causes found:

1. Historical rows had never been backfilled.
2. [backend/opportunities/core/pipeline_flow.py](/d:/Documents/BidWise/backend/opportunities/core/pipeline_flow.py) materialized opportunities without scheduling ESCO normalization.
3. [backend/users/tasks.py](/d:/Documents/BidWise/backend/users/tasks.py) only triggered resume semantic enrichment for active resumes.
4. Docker/runtime drift caused missing normalization fields in `backend/users/models.py`.

Repairs:
- schedule opportunity normalization from `pipeline_flow`
- run resume semantics for already parsed inactive resumes
- restore missing profile/resume normalization model fields in runtime
- add batch-safe recovery and reporting

Key files:
- [backend/opportunities/core/pipeline_flow.py](/d:/Documents/BidWise/backend/opportunities/core/pipeline_flow.py)
- [backend/users/tasks.py](/d:/Documents/BidWise/backend/users/tasks.py)
- [backend/users/models.py](/d:/Documents/BidWise/backend/users/models.py)
- [backend/ai/esco_normalization_recovery.py](/d:/Documents/BidWise/backend/ai/esco_normalization_recovery.py)
- [backend/ai/management/commands/backfill_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/backfill_esco_normalization.py)
- [backend/ai/management/commands/report_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/report_esco_normalization.py)

### Phase 10. CV candidate quality filtering and fast cleanup mode

Problem discovered:
- CV coverage at entity level became good
- but top unmatched CV skills were polluted by phrase fragments and generic business language

Examples:
- `d`
- `et développer un portefeuille de clients`
- `les interlocuteurs clé`
- `ouvrir de nouveaux comptes`
- `opportunités`

This was an extraction quality issue, not an ESCO index availability issue.

Implemented:
- resume candidate quality filter
- rejected-candidate analytics
- unmatched reason reporting
- fast `candidate_cleanup` mode for resume backfills

Key files:
- [backend/users/resume_semantic/candidate_quality.py](/d:/Documents/BidWise/backend/users/resume_semantic/candidate_quality.py)
- [backend/users/resume_semantic/models.py](/d:/Documents/BidWise/backend/users/resume_semantic/models.py)
- [backend/users/resume_semantic/service.py](/d:/Documents/BidWise/backend/users/resume_semantic/service.py)
- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
- [backend/ai/esco_normalization_recovery.py](/d:/Documents/BidWise/backend/ai/esco_normalization_recovery.py)
- [backend/ai/management/commands/backfill_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/backfill_esco_normalization.py)

New capability:
- `--resume-mode candidate_cleanup`

This mode:
- reuses already stored resume candidates
- does not rerun the full semantic CV pipeline
- refreshes normalized payloads and candidate-quality analytics safely

### Phase 11. BidWise custom alias layer

Goal:
- create a durable, reviewable, data-driven coverage layer on top of official ESCO

Implemented:
- `BidWiseSkillAlias` model
- cached in-memory alias loading inside the ESCO skill index
- exact custom alias matching before semantic fallback
- CSV loader command for approved aliases
- review-oriented alias suggestion command

Key files:
- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)
- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
- [backend/ai/management/commands/load_bidwise_skill_aliases.py](/d:/Documents/BidWise/backend/ai/management/commands/load_bidwise_skill_aliases.py)
- [backend/ai/management/commands/suggest_skill_aliases.py](/d:/Documents/BidWise/backend/ai/management/commands/suggest_skill_aliases.py)
- [backend/ai/skill_alias_suggestions.py](/d:/Documents/BidWise/backend/ai/skill_alias_suggestions.py)

### Phase 12. First approved alias seed and official-collision repair

Goal:
- load the first very conservative alias seed from real unmatched production data
- repair exact-match collisions where a single official ESCO concept competes with legacy prototype rows

Implemented:
- first approved alias seed file:
  - [backend/ai/data/bidwise_skill_aliases_seed_v1.csv](/d:/Documents/BidWise/backend/ai/data/bidwise_skill_aliases_seed_v1.csv)
- conservative exact-match repair in [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
  - prefer the unique official ESCO concept when an exact surface collides with legacy duplicates
  - promote a unique official `alt_label` over a legacy preferred label only when the official match is explicit and not just a hidden label

First seed content:
- `excel` -> `use spreadsheets software`

Why only one alias in `seed_v1`:
- it was the highest-frequency safe unmatched opportunity skill
- other top unmatched terms such as `Vente`, `Gestion`, `Marketing`, `Finance`, `sage`, `Qualité`, and `Hôtellerie` were still too broad or too ambiguous for automatic promotion

Measured impact after loading the seed and forcing a backfill:
- opportunities official ESCO coverage: `41.17% -> 64.13%`
- opportunities official matched entries: `426 -> 634`
- opportunities unmatched entries: `1846 -> 1638`
- resumes official ESCO coverage: `96.77% -> 100%`
- profiles official ESCO coverage on the current small sample: `0% historical observation -> 33.33%`

Interpretation:
- the gain came from two safe levers:
  - the approved `excel` alias
  - official-vs-legacy exact-match repair for common stack terms such as `Python` and `JavaScript`
- this validates the alias-layer approach without prematurely mapping broad business-domain words

### Phase 13. Second approved alias seed

Goal:
- extend coverage with a few more high-frequency, domain-safe aliases
- keep the seed limited to terms with clear ESCO destinations

Implemented:
- second approved alias seed:
  - [backend/ai/data/bidwise_skill_aliases_seed_v2.csv](/d:/Documents/BidWise/backend/ai/data/bidwise_skill_aliases_seed_v2.csv)

Seed `v2` content:
- `AUTOCAD` -> `CAD software`
- `Hôtellerie` -> `hotel operations`
- `Maintenance Industrielle` -> `maintain industrial equipment`
- `controle qualite` -> `conduct quality control analysis`

Measured impact after loading `seed_v2` and forcing an opportunity backfill:
- opportunities official ESCO coverage: `64.13% -> 71.55%`
- opportunities official matched entries: `634 -> 711`
- opportunities unmatched entries: `1638 -> 1561`

New top matched skills introduced by `seed_v2`:
- `conduct quality control analysis`: `39`
- `hotel operations`: `16`
- `CAD software`: `14`
- `maintain industrial equipment`: `10`

Important interpretation:
- `seed_v2` shows that careful manual review can still yield meaningful gains without relaxing semantic thresholds
- the remaining unmatched head is now dominated by broader domain words such as `Vente`, `Gestion`, `Marketing`, `Finance`, `Tourisme`, and `Management`, which need a stricter human taxonomy decision before promotion

## 4. Current architecture state

### ESCO data layer

Official ESCO is now local and queryable through:
- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)
- [backend/ai/esco_catalog_ingestion.py](/d:/Documents/BidWise/backend/ai/esco_catalog_ingestion.py)

### Normalization layer

Main service:
- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)

Cached index:
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)

Storage wrapper:
- [backend/ai/esco_skill_storage.py](/d:/Documents/BidWise/backend/ai/esco_skill_storage.py)

### Pipeline integration

Opportunities:
- [backend/opportunities/processing.py](/d:/Documents/BidWise/backend/opportunities/processing.py)
- [backend/opportunities/core/pipeline_flow.py](/d:/Documents/BidWise/backend/opportunities/core/pipeline_flow.py)

Profiles:
- [backend/users/serializers.py](/d:/Documents/BidWise/backend/users/serializers.py)

Resumes:
- [backend/users/resume_semantic/service.py](/d:/Documents/BidWise/backend/users/resume_semantic/service.py)
- [backend/users/tasks.py](/d:/Documents/BidWise/backend/users/tasks.py)

### Backfill and reporting

- [backend/ai/esco_normalization_recovery.py](/d:/Documents/BidWise/backend/ai/esco_normalization_recovery.py)
- [backend/ai/management/commands/backfill_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/backfill_esco_normalization.py)
- [backend/ai/management/commands/report_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/report_esco_normalization.py)

## 5. Main problems found during the integration

### Problem A. Temporary prototype mixed with official ESCO

Symptoms:
- `ReactJs` matched legacy `esco:skill_react`
- `Python3` matched official ESCO URI

Meaning:
- the system temporarily mixed legacy and official concepts

Mitigation:
- storage layer filters non-official URIs when `official_only=True`
- reporting now tracks `legacy_uri_filtered`

Relevant files:
- [backend/ai/esco_skill_storage.py](/d:/Documents/BidWise/backend/ai/esco_skill_storage.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)

### Problem B. Normalized fields existed but stayed empty

Symptoms:
- normalized storage rarely populated in real rows

Real causes:
- no historical backfill
- missing opportunity scheduling path
- inactive resume path skipped
- runtime drift in user/profile models

Mitigation:
- recovery commands
- path fixes
- runtime model repair

### Problem C. Resume backfill was too slow

Observed:
- `backfill_esco_normalization --target resumes --batch-size 1 --limit 1` could take many minutes

Reason:
- it launched the full semantic CV pipeline in a fresh Django process
- cold-start CPU model loads were repaid for very small batches

Mitigation:
- `--resume-mode candidate_cleanup`

### Problem D. CV unmatched skills contained phrase noise

Observed:
- phrase fragments were reaching ESCO normalization

Mitigation:
- resume candidate quality filter
- rejected-candidate analytics
- top rejected candidate reporting

### Problem E. Official ESCO alone is not enough for market coverage

Observed:
- some modern stack terms, local aliases, tools, and product names still remain unmatched

Implication:
- ESCO is the canonical backbone
- a BidWise custom alias layer is still needed

Concrete examples seen in practice:
- modern frontend stack variants
- business software aliases such as `Excel` and `SAP`
- local FR wording for roles and transferable skills
- user-entered shorthand that is valid product language but not a direct official ESCO label

## 6. Current coverage snapshot

These numbers reflect the state after the recovery and resume candidate-cleanup work.

### Opportunities

- payload coverage: `100%` on eligible historical rows
- official ESCO match coverage: `41.21%`
- eligible rows with source skills: `563`
- entities with at least one official ESCO match: `232`

Interpretation:
- this is much healthier than the pre-backfill state
- but `41.21%` official match coverage is still too low for a production-grade skill-driven recommendation layer
- a BidWise custom alias layer is therefore the next practical coverage unlock

### Profiles

- payload coverage: `100%` on eligible rows
- eligible rows with source skills: `3`
- official matches currently observed on those rows: `0`

This does **not** mean profile normalization is broken.
It means the currently available test/profile skill inputs are not strongly covered by official ESCO after conservative filtering.

Interpretation:
- local market wording and user-entered aliases are under-covered
- FR/EN variants and Tunisia-specific phrasing need a custom alias layer on top of official ESCO

### Resumes

After candidate cleanup:
- payload coverage: `100%`
- official match coverage: `96.77%`
- `matched_entries`: `54`
- `unmatched_entries`: `573`

Top rejected candidate reasons:
- `phrase_fragment`: `209`
- `sentence_like_fragment`: `54`
- `phrase_too_long`: `45`
- `generic_business_term`: `34`
- `action_phrase`: `19`

Top unmatched reasons after filtering:
- `semantic_below_threshold`
- `semantic_surface_bridge_missing`
- `legacy_uri_filtered`
- `query_too_short_for_semantic`
- `ambiguous_exact_match`

Interpretation:
- extraction noise was significantly reduced
- but a substantial unmatched tail remains
- the next improvement should target coverage via aliases, not lower thresholds first

## 7. Commands used and current operational commands

### 7.1 ESCO catalog import

```bash
docker compose exec backend python manage.py import_esco_catalog --batch-size 2000
```

Purpose:
- import official EN/FR ESCO CSV data into internal tables

### 7.2 ESCO skill embedding generation

```bash
docker compose exec backend python manage.py generate_esco_skill_embeddings --batch-size 64
```

Purpose:
- generate and store ESCO vectors plus embedding metadata

### 7.3 Full normalization backfill

All targets:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target all --batch-size 100
```

Only opportunities:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target opportunities --batch-size 100
```

Only profiles:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target profiles --batch-size 100
```

Only resumes with full semantic rerun:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target resumes --resume-mode full --batch-size 10
```

### 7.4 Fast resume cleanup mode

Recommended for already parsed resumes:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target resumes --resume-mode candidate_cleanup --batch-size 20
```

Important note:
- avoid `--batch-size 1 --limit 1` when measuring performance on resumes
- it pays the full cold-start cost in the worst possible way

### 7.5 Coverage and diagnostics report

```bash
docker compose exec backend python manage.py report_esco_normalization --target all --top-n 10 --json
```

Resume-specific diagnostics:

```bash
docker compose exec backend python manage.py report_esco_normalization --target resumes --top-n 10 --json
```

### 7.6 Alias suggestion review

Generate a review-ready unmatched-skill analysis:

```bash
docker compose exec backend python manage.py suggest_skill_aliases --target all --top-n 200 --min-count 2 --json
```

Write a CSV for human review:

```bash
docker compose exec backend python manage.py suggest_skill_aliases --target all --top-n 300 --min-count 2 --output backend/ai/data/bidwise_skill_alias_review.csv
```

Purpose:
- aggregate frequent unmatched skills from opportunities, profiles, and resumes
- classify them as `official_match`, `needs_review`, `noise`, or `ambiguous`
- provide nearest ESCO candidates for human alias review without modifying runtime behavior

### 7.7 Load approved BidWise aliases

Load a reviewed alias CSV:

```bash
docker compose exec backend python manage.py load_bidwise_skill_aliases backend/ai/data/bidwise_skill_alias_review.csv
```

Load the first approved seed inside Docker:

```bash
docker compose exec backend python manage.py load_bidwise_skill_aliases /app/ai/data/bidwise_skill_aliases_seed_v1.csv
```

Purpose:
- persist review-approved aliases in the database
- make them available in the cached ESCO normalization index
- allow future backfills to consume them without code edits

Force backfill after alias or exact-match logic changes:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target opportunities --batch-size 100 --force
docker compose exec backend python manage.py backfill_esco_normalization --target profiles --batch-size 100 --force
docker compose exec backend python manage.py backfill_esco_normalization --target resumes --resume-mode candidate_cleanup --batch-size 20 --force
```

### 7.8 Validation commands

System checks:

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
```

Targeted ESCO tests:

```bash
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_esco_skill_infrastructure
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_esco_skill_normalization
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_esco_catalog_ingestion
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_esco_normalization_storage_integration
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_esco_normalization_recovery
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_resume_semantic
```

Recommendation regression checks:

```bash
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_recommendation_normalized_skill_bonus
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_recommendation_experience_gap_penalty
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_user_recommendations
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_recommendation_quality_gates
docker compose run --rm backend python manage.py test --keepdb --noinput tests.test_recommendation_explainability
```

## 8. Main files by responsibility

### ESCO models and index

- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)
- [backend/ai/esco_skill_embeddings.py](/d:/Documents/BidWise/backend/ai/esco_skill_embeddings.py)

### ESCO catalog import

- [backend/ai/esco_catalog_ingestion.py](/d:/Documents/BidWise/backend/ai/esco_catalog_ingestion.py)
- [backend/ai/management/commands/import_esco_catalog.py](/d:/Documents/BidWise/backend/ai/management/commands/import_esco_catalog.py)

### Skill normalization

- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
- [backend/ai/esco_skill_storage.py](/d:/Documents/BidWise/backend/ai/esco_skill_storage.py)

### BidWise alias layer

- [backend/ai/models.py](/d:/Documents/BidWise/backend/ai/models.py)
- [backend/ai/esco_skill_index.py](/d:/Documents/BidWise/backend/ai/esco_skill_index.py)
- [backend/ai/esco_skill_normalization.py](/d:/Documents/BidWise/backend/ai/esco_skill_normalization.py)
- [backend/ai/management/commands/load_bidwise_skill_aliases.py](/d:/Documents/BidWise/backend/ai/management/commands/load_bidwise_skill_aliases.py)
- [backend/ai/management/commands/suggest_skill_aliases.py](/d:/Documents/BidWise/backend/ai/management/commands/suggest_skill_aliases.py)
- [backend/ai/skill_alias_suggestions.py](/d:/Documents/BidWise/backend/ai/skill_alias_suggestions.py)

### Recommendation-safe enrichment

- [backend/ai/esco_recommendation_signals.py](/d:/Documents/BidWise/backend/ai/esco_recommendation_signals.py)
- [backend/ai/recommendation_service.py](/d:/Documents/BidWise/backend/ai/recommendation_service.py)
- [backend/ai/user_features.py](/d:/Documents/BidWise/backend/ai/user_features.py)
- [backend/ai/retrieval.py](/d:/Documents/BidWise/backend/ai/retrieval.py)

### Backfill and diagnostics

- [backend/ai/esco_normalization_recovery.py](/d:/Documents/BidWise/backend/ai/esco_normalization_recovery.py)
- [backend/ai/management/commands/backfill_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/backfill_esco_normalization.py)
- [backend/ai/management/commands/report_esco_normalization.py](/d:/Documents/BidWise/backend/ai/management/commands/report_esco_normalization.py)

### Resume semantic quality

- [backend/users/resume_semantic/candidate_quality.py](/d:/Documents/BidWise/backend/users/resume_semantic/candidate_quality.py)
- [backend/users/resume_semantic/service.py](/d:/Documents/BidWise/backend/users/resume_semantic/service.py)
- [backend/users/resume_semantic/extraction.py](/d:/Documents/BidWise/backend/users/resume_semantic/extraction.py)
- [backend/users/resume_semantic/esco_mapping.py](/d:/Documents/BidWise/backend/users/resume_semantic/esco_mapping.py)
- [backend/users/resume_semantic/models.py](/d:/Documents/BidWise/backend/users/resume_semantic/models.py)

## 9. Remaining legacy and hybrid areas to watch

These were identified but not aggressively deleted yet:

- legacy `esco:skill_*` rows still exist in the ESCO skill table
- [backend/ai/esco.py](/d:/Documents/BidWise/backend/ai/esco.py) appears to be legacy/duplicate territory and should be reviewed carefully before deletion
- old 43-skill prototype behavior is still visible in some historical rows and reports through `legacy_uri_filtered`
- `backend/ai/esco_mapper.py` remains active for occupation-family logic and should not be confused with the skill-normalization service

Guideline:
- isolate first
- measure usage
- only then remove

## 10. Recommended next step

The next recommended production step is:

> build a BidWise custom skill alias layer, backed by a small offline evaluation set.

Why this is the right next move:
- infrastructure is now stable
- normalized fields are finally populated
- ESCO coverage is real but still incomplete for modern tools and market-specific aliases
- lowering semantic thresholds now would increase false positives

This should be treated as Priority 1.

### Proposed next implementation scope

#### 10.1 Add a `BidWiseSkillAlias` model

Suggested fields:
- `alias`
- `normalized_key`
- `language`
- `target_esco_uri`
- `source`
- `status`
- `notes`

#### 10.2 Use alias matching before semantic fallback

Recommended matching order:
1. exact official preferred label
2. exact official alt/hidden label
3. exact BidWise custom alias
4. semantic fallback

#### 10.3 Build a labeled evaluation set

Take the top unmatched items from:
- opportunities
- profiles
- resumes

Manually classify them as:
- `official_esco_match`
- `custom_alias_needed`
- `noise`
- `ambiguous`

#### 10.4 Re-measure coverage after aliases

Re-run:

```bash
docker compose exec backend python manage.py report_esco_normalization --target all --top-n 20 --json
```

Key outcomes to compare:
- official matches
- custom alias matches
- semantic matches
- unmatched noise

## 11. Offline evaluation status and next benchmark step

Offline evaluation is **not absent from the codebase**, but it is not yet tied strongly enough to the new ESCO normalization coverage work.

What already exists:
- internal benchmark framework
- Precision@K
- Recall@K
- noise rate
- false positive rate
- MRR
- CrossEncoder uplift reporting
- sparse-profile robustness
- CV uplift reporting
- multilingual robustness

Key files:
- [backend/ai/recommendation_benchmark/runner.py](/d:/Documents/BidWise/backend/ai/recommendation_benchmark/runner.py)
- [backend/ai/recommendation_benchmark/metrics.py](/d:/Documents/BidWise/backend/ai/recommendation_benchmark/metrics.py)
- [backend/opportunities/management/commands/benchmark_recommendations.py](/d:/Documents/BidWise/backend/opportunities/management/commands/benchmark_recommendations.py)

Useful command:

```bash
docker compose exec backend python manage.py benchmark_recommendations --no-write-report
```

Current limitation:
- the benchmark exists
- but it is not yet being used as the main acceptance gate for ESCO normalization changes
- and it does not yet contain a focused hand-labeled subset specifically for ESCO alias coverage

Recommended next benchmark action:
- create a small labeled set of real Tunisia-relevant profile/job pairs
- explicitly measure before/after impact of the alias layer
- use benchmark deltas, not intuition alone, to validate normalization improvements

## 12. Operational guidance

### For bulk resume cleanup

Use:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target resumes --resume-mode candidate_cleanup --batch-size 20
```

Not:

```bash
docker compose exec backend python manage.py backfill_esco_normalization --target resumes --batch-size 1 --limit 1
```

Reason:
- the latter exaggerates cold-start cost and is not representative of real batch performance

### For debugging why a skill did not normalize

Use:
- `report_esco_normalization` top unmatched skills
- top unmatched reasons
- top rejected resume candidates
- top rejected candidate reasons

### For recommendation safety

Do not:
- inject runtime normalization in recommendation calls
- lower semantic thresholds aggressively
- expand through occupation graphs yet
- replace raw overlap logic yet

## 13. Final status

BidWise now has:

- local official ESCO catalog
- multilingual skill ingestion
- vectorized ESCO index with metadata
- isolated conservative skill normalization
- normalized storage in opportunities, profiles, and resumes
- recovery and reporting commands
- recommendation-safe normalized overlap enrichment
- resume candidate quality analytics

The integration is no longer just architectural. It is now operational.

The remaining work is mainly:
- coverage improvement
- alias curation
- evaluation discipline
- careful reduction of the unmatched tail
