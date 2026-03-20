# BidWise - Data Acquisition Layer Architecture

## 1. System Overview
The Data Acquisition layer is responsible for collecting external job opportunities and transforming them into consistent, trusted records for BidWise.

Its role in the platform is:
- Feed the opportunities catalog used by the web/mobile browsing UI.
- Build a clean, structured dataset for Sprint 3 recommendation logic.
- Isolate scraping complexity from API and frontend code.

High-level flow:

```text
External Job Sites
   -> Scrapers (requests + BeautifulSoup)
   -> Normalization Layer (parser.py)
   -> Storage Layer (pipeline.py + Django ORM)
   -> PostgreSQL (Opportunite, SourceOpportunite)
```

## 2. Scraper Architecture
The scraping module is intentionally modular:

- `scraper_base.py`
  - Defines `BaseOpportunityScraper` (abstract contract).
  - Any scraper must implement `fetch_raw_records()`.
  - Shared `collect()` returns a list of raw records.

- Site-specific scraper (example: `keejob_scraper.py`)
  - Contains source-specific URL, selectors, and extraction logic.
  - Produces raw records in a common dictionary style expected by normalization.

- Command registry (`collect_opportunities.py`)
  - Maps source keys (example: `keejob`) to scraper classes.
  - Makes adding a new source a simple registration step.

Why this design is scalable:
- New source integration does not require changing parser or pipeline internals.
- Scraper failures are isolated by source.
- Common ingestion/storage logic is reused for every source.

## 3. Selector Strategy
Each field uses a selector list, for example:
- `TITLE_SELECTORS`
- `COMPANY_SELECTORS`
- `LOCATION_SELECTORS`

How it works:
- Selectors are evaluated in order.
- First selector that returns non-empty text is used.
- If one selector fails after DOM changes, fallback selectors still allow extraction.

Benefits:
- Priority control: preferred DOM path first.
- Resilience: reduced breakage when sites slightly change HTML structure.
- Maintainability: selector updates are local to one scraper file.

## 4. Anti-Bot Strategy
BidWise follows ethical and legal scraping practices:

- Respect website terms and `robots.txt` where applicable.
- Use realistic HTTP headers (`User-Agent`, `Accept-Language`) to reduce false bot blocking.
- Apply request rate limiting (delay between requests) and page limits to avoid aggressive crawling.
- Avoid high-concurrency bursts and repeated retries.
- Do not bypass authentication, CAPTCHA, or anti-bot protections.

Operational rule:
- If a site blocks normal compliant requests, treat that source as unavailable or switch source, not bypass security controls.

## 5. Error Tolerance and Stability
The acquisition layer is defensive by design:

- Request exception handling:
  - `_safe_get_soup()` catches `requests` errors and returns `None` instead of crashing.
- Fallback selectors:
  - Multiple selectors per field reduce extraction failures.
- Duplicate URL filtering:
  - `seen_urls` prevents processing the same listing card multiple times in one run.
- Defensive parsing:
  - Records missing critical fields (title/date) are skipped during normalization with tracked errors.

Result:
- One bad page/card should not stop the full ingestion run.

## 6. Data Normalization
Raw records from scrapers are converted to a unified schema in `parser.py` (`normalize_opportunity`).

Responsibilities of normalization:
- Accept source-native keys (`title`, `publication_date`) and map to model fields (`titre`, `date_publication`).
- Standardize type and status using maps:
  - `TYPE_MAP` -> `TypeOpportunite`
  - `STATUS_MAP` -> `StatutOpportunite`
- Parse dates into Python `date` objects.
- Validate required fields and reject invalid records early.

Example raw record:

```json
{
  "title": "Data Analyst",
  "description": "Analyze business data...",
  "publication_date": "2026-03-15",
  "source_name": "Keejob",
  "source_url": "https://www.keejob.com/offres-emploi/",
  "source_type": "SITE_EMPLOI"
}
```

Example normalized payload returned by parser:

```json
{
  "titre": "Data Analyst",
  "description": "Analyze business data...",
  "type_opportunite": "EMPLOI",
  "statut": "ACTIVE",
  "date_publication": "2026-03-15",
  "date_limite": null,
  "source_name": "Keejob",
  "source_url": "https://www.keejob.com/offres-emploi/",
  "source_type": "SITE_EMPLOI"
}
```

## 7. Storage Layer
`pipeline.py` persists normalized data with Django ORM:

- Source persistence:
  - `SourceOpportunite.objects.get_or_create(nom=...)`
  - Updates source URL/type if they changed.

- Opportunity persistence:
  - `Opportunite.objects.update_or_create(...)`
  - Dedup key: `(titre, source, date_publication)`
  - Updates mutable fields (`description`, `statut`, `date_limite`, etc.) when record already exists.

Data integrity:
- DB-level unique constraint on `(titre, source, date_publication)` prevents duplicate rows.
- App-level upsert (`update_or_create`) keeps ingestion idempotent.

Performance support:
- Indexes on filter/order fields (`statut`, `date_publication`, `date_limite`, `date_creation`, and composite indexes) improve query speed for API browsing and future recommendation queries.

## 8. Extensibility
To add a new source (for example a new job board):

1. Create `opportunities/scraping/<new_source>_scraper.py`.
2. Extend `BaseOpportunityScraper`.
3. Implement `fetch_raw_records()` returning the expected raw dictionary format.
4. Add source class to `SCRAPER_REGISTRY` in `collect_opportunities.py`.
5. Run:
   - `python manage.py collect_opportunities --source <new_source>`

Because normalization and storage are centralized, new sources reuse the same validation, deduplication, and persistence workflow with minimal code.

