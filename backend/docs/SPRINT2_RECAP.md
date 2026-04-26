# Sprint 2 - Technical recap

Last updated: 2026-04-26

## Verdict

Sprint 2 is complete for the opportunities pipeline scope.

The original Sprint 2 target was the backend data layer behind opportunity discovery. That scope is now implemented end to end: collection, raw persistence, normalization, enrichment, quality scoring, materialization, API exposure, embeddings, and similarity.

## Scope delivered

| Goal | State | Evidence in code |
| --- | --- | --- |
| Scraping stability | Complete | `opportunities/scraping/pipeline.py`, active connectors in `opportunities/scraping/sources/`, fixture-based scraper tests |
| Normalization | Complete | `opportunities/normalization/service.py` |
| Enrichment | Complete | `opportunities/enrichment/text_enrichment.py` |
| Quality gate | Complete | `opportunities/quality/quality_gate.py`, `opportunities/scoring/quality.py` |
| Materialization | Complete | `opportunities/materialization/service.py` |
| API | Complete | `opportunities/views.py`, `opportunities/filters.py`, `opportunities/serializers.py` |
| Similarity | Complete | `opportunities/similarity.py`, `opportunities/embeddings/service.py` |

## Active source coverage

Sprint 2 sign-off sources:
- Keejob
- EmploiTunisie

Additional connectors already present in the current codebase:
- LinkedIn
- MarchesPublics

The active scraper registry lives in `opportunities/management/commands/collect_opportunities.py`.

## Actual pipeline path

`Scraper -> RawOpportunite -> normalization -> enrichment -> quality gate -> materialization -> Opportunite -> embeddings -> similarity -> DRF API`

Current implementation modules:
- `opportunities/scraping/pipeline.py`
- `opportunities/processing.py`
- `opportunities/normalization/service.py`
- `opportunities/enrichment/text_enrichment.py`
- `opportunities/quality/quality_gate.py`
- `opportunities/materialization/service.py`
- `opportunities/dataset_metrics.py`
- `opportunities/similarity.py`
- `opportunities/api/services/opportunities.py`

## What is materially in place

- Raw shadow storage with identity keys on `source_record_id` and `source_item_url`.
- Replay-safe processing from `RawOpportunite` to `Opportunite`.
- Canonical parsing for dates, statuses, types, cities, contracts, education, URLs, and experience ranges.
- Structured enrichment for salary, skills, languages, and description-derived signals.
- Non-destructive merge rules for canonical updates.
- Dataset and pipeline metrics commands for operational visibility.
- Similarity endpoint backed by embeddings, with optional pgvector acceleration and Python fallback.
- Web and mobile clients already consuming the API layer.

## Testing surface

Primary Sprint 2 backend coverage lives in:
- `tests.tests.RawNormalizationTests`
- `tests.tests.EmploiTunisieScraperStructuredParsingTests`
- `tests.tests.OpportunityTextEnrichmentTests`
- `tests.tests.OpportunityMaterializationTests`
- `tests.tests.OpportuniteAPITests`
- `tests.tests.PipelineTests`

Extended regression coverage also exists for:
- `tests.test_scrapers`
- `tests.test_linkedin_scraper`
- `tests.tests_quality`
- `tests.tests_embeddings`
- `tests.tests_marchespublics`
- `tests.test_nlp_preprocessing`

## Non-blocking backlog

- hard duplicate cleanup in the existing dataset,
- release smoke run before final push in a live Docker environment,
- Sprint 3 personalization and user action features.

## Documentation policy

This recap is now the single Sprint 2 summary document. The old one-off closure snapshot has been removed to avoid split sources of truth.
