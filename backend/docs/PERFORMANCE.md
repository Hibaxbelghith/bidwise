# Opportunity Search And Filtering Performance

This document covers the production search/filtering layer for the public opportunity browser.
It does not modify recommendation, embeddings, pgvector retrieval, CrossEncoder reranking, or AI scoring.

## API Contract

The browser sends only query params:

- `type` or `type_opportunite`
- `location`, `city`, or `ville`
- `search`
- `source` as source id or source name
- `work_mode`
- `experience_level`
- `status` or `statut`
- `sort`
- `page`
- `page_size`

The backend owns filtering, sorting, pagination, facets, counts, and search matching.
The paginated list response keeps the existing DRF shape and adds `facets`:

```json
{
  "count": 12452,
  "next": "...",
  "previous": null,
  "results": [],
  "facets": {
    "types": [{"key": "EMPLOI", "count": 8200}],
    "locations": [{"key": "Tunis", "count": 3200}],
    "sources": [{"key": "LinkedIn", "id": 3, "count": 5400}]
  }
}
```

A lightweight facets-only endpoint is also available:

```text
GET /api/opportunities/facets/
```

## Filtering Architecture

Filtering is implemented through `OpportuniteFilterSet` and the opportunity queryset service.

Why:

- Keeps filtering server-side and prevents frontend-side dataset filtering.
- Keeps existing aliases (`type_opportunite`, `statut`, `ville`) while adding UX-friendly aliases (`type`, `status`, `location`).
- Allows source filtering by numeric id or source name.
- Keeps default public listing scoped to active opportunities unless a status is explicitly requested.

Default sort:

```text
quality_score DESC, date_publication DESC, id DESC
```

Why:

- `quality_score` keeps higher-quality opportunities first.
- `date_publication` fixes stale ordering for equal quality.
- `id` makes pagination stable.

## Faceted Search

Facets are built from the already-filtered queryset, so counts respect active filters.

Current facets:

- `types`
- `locations`
- `sources`
- `work_modes`
- `experience_levels`
- `statuses`

Why:

- One source of truth for list count and filter counts.
- Dynamic counts support sidebar pills/chips without loading all rows in the frontend.
- The response is ready for infinite scroll or search-as-you-type UX.

## Search Architecture

Search uses PostgreSQL-native tools:

- Full-text search with `simple` config for title, company, location, and description.
- `pg_trgm` for typo-tolerant matching on short fields: title, company, location.
- Prefix full-text query terms for partial matching.
- No Elasticsearch/OpenSearch or paid infrastructure.

Why:

- Full-text search is better for common words in descriptions.
- Trigram is better for typos and partial short-field matching.
- Keeping typo search off long descriptions avoids expensive similarity scans.

The `simple` full-text config is intentional: it is more predictable for multilingual data than an English/French stemmer when listings mix French, English, Arabic transliteration, and source-specific formatting.

## Indexing Strategy

Migration `0030_opportunity_search_filter_indexes.py` adds:

- `source_nom_idx`
- `opp_active_quality_date_idx`
- `opp_status_type_quality_date_idx`
- `opp_status_location_quality_date_idx`
- `opp_status_source_quality_date_idx`
- `opp_status_workmode_quality_date_idx`
- `opp_status_created_idx`
- `opp_role_experience_idx`
- `opp_title_trgm_idx`
- `opp_company_trgm_idx`
- `opp_location_trgm_idx`
- `opp_description_trgm_idx`

Migration `0031_opportunity_search_vector_index.py` adds:

- `opp_search_vector_gin_idx`

Why:

- Composite B-tree indexes match common filter + sort access paths.
- Sort indexes support stable page-number pagination without random ordering.
- Trigram GIN indexes support partial and typo-tolerant text matching.
- Full-text GIN index supports indexed word search over multi-field opportunity text.

## Query Optimization

The list queryset uses:

- `select_related("source", "organisation")`
- `defer("embedding_vector", "embedding_vector_pg")`
- capped `page_size` with `max_page_size = 50`
- stable ordering by score/date/id
- query-count tests for filtered list requests

Why:

- Avoids N+1 source/owner queries.
- Avoids fetching vector payloads that are not serialized in list/detail responses.
- Prevents unbounded frontend-style reads.

## Pagination Strategy

Current strategy: optimized page-number pagination.

Why this is acceptable now:

- Existing API contract remains intact.
- Page size is capped.
- Ordering is stable.
- Composite indexes support the most common sorted access paths.

Known limitation:

- Very deep page numbers still use offset pagination and can slow down at high scale.
- If users frequently jump to very deep pages at 100k+ rows, add a cursor endpoint while keeping the existing page-number endpoint for compatibility.

## Caching Strategy

Facets are cached with Redis through Django cache:

- Keyed by normalized filter params.
- Short TTL: `OPPORTUNITY_FACET_CACHE_TTL_SECONDS`, default `60`.
- Versioned by `OPPORTUNITY_FACET_CACHE_VERSION`.
- Results themselves are not cached.

Why:

- Facet aggregations are the repeated expensive part for anonymous browsing.
- Short TTL limits stale counts after scraper updates.
- No invalidation-heavy architecture is required.

## Observability

The opportunity API adds:

- `X-BidWise-Query-Time-Ms`
- `X-BidWise-Query-Count` when Django query logging is available
- slow-query logging controlled by `OPPORTUNITY_SLOW_QUERY_MS`, default `250`
- benchmark command:

```bash
python manage.py benchmark_opportunity_search --iterations 3 --json
python manage.py benchmark_opportunity_search --synthetic-size 100000 --iterations 3 --json
```

The benchmark command reports average time, worst-case time, average query count, and worst query count per scenario.

## Measured Local Results

Measured in local Docker on the current dataset: `2,825` active opportunities. These are real local measurements, not production guarantees.

Cold facet cache:

| Scenario | Count | Avg | Worst | Queries |
| --- | ---: | ---: | ---: | ---: |
| baseline quality | 2,825 | 30.79 ms | 41.65 ms | 8 |
| newest page 3 | 2,825 | 22.51 ms | 24.00 ms | 8 |
| job remote Tunis | 9 | 17.54 ms | 17.90 ms | 8 |
| search python | 1,254 | 814.10 ms | 827.99 ms | 10 |
| facets job | 2,270 | 35.76 ms | 40.66 ms | 8 |

Warm facet cache:

| Scenario | Count | Avg | Worst | Queries |
| --- | ---: | ---: | ---: | ---: |
| baseline quality | 2,825 | 19.42 ms | 32.86 ms | 2 |
| newest page 3 | 2,825 | 11.05 ms | 11.60 ms | 2 |
| job remote Tunis | 9 | 9.23 ms | 10.84 ms | 2 |
| search python | 1,254 | 250.21 ms | 290.73 ms | 4 |
| facets job | 2,270 | 7.37 ms | 9.68 ms | 2 |

Interpretation:

- Normal filtering/facets are healthy locally.
- The heavy path is common-term text search with many matches.
- Redis facet caching materially reduces query count and latency.
- Search at 100k+ rows should be benchmarked with realistic scraped text before making SLA claims.

## Remaining Bottlenecks

- Common-term search still does meaningful database work because it can match many rows.
- Deep offset pagination can degrade as page numbers grow.
- Facets are dynamic and correct, but each cold facet request still performs multiple aggregations.
- Description search is indexed, but long unstructured scraped text remains inherently heavier than normalized short fields.

## Future Production Recommendations

Without changing infrastructure:

- Add cursor pagination for infinite scroll while preserving page-number pagination.
- Add an optional `include_facets=0` mode for search-as-you-type result-only calls.
- Track real production slow query logs and add partial indexes once dominant filters are known.
- Consider a materialized `search_document` column maintained during materialization if common-term search remains hot at 100k+ rows.
- Keep `page_size` capped and debounce search inputs on the frontend.
