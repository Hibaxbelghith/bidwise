# Sprint 2 - Testing guide

Last updated: 2026-04-26

This guide is the fastest way to validate the Sprint 2 opportunities pipeline before a release or a demo.

## 1. Preconditions

From the repository root:

```bash
docker compose up -d
docker compose ps
```

Expected:
- `backend` is `Up`
- `db` is healthy

Active source keys in the current registry:
- `keejob`
- `emploitunisie`
- `linkedin`
- `marchespublics`

## 2. Five-minute pipeline smoke test

### Step 1 - Collect source data

```bash
docker compose run --rm backend python manage.py collect_opportunities --source emploitunisie
```

Expected:
- `Created` or `Updated` is greater than zero
- no crash

### Step 2 - Process pending raw records

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.processing import process_pending_raw_opportunities; print(process_pending_raw_opportunities(limit=1000))"
```

Expected:
- `materialized > 0`
- `errors = 0` or a very small explainable number

### Step 3 - Check pipeline metrics

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.dataset_metrics import compute_pipeline_metrics; print(compute_pipeline_metrics())"
```

Expected:
- controlled backlog,
- high processing success rate,
- no unexpected rise in rejected records.

### Step 4 - Check dataset metrics

```bash
docker compose run --rm backend python manage.py dataset_metrics
```

Expected:
- HTML coverage is visible,
- invalid URL exclusions are visible,
- metrics match the real database state.

### Step 5 - Run dataset audit

```bash
docker compose run --rm backend python manage.py audit_opportunities_dataset
```

Expected:
- no critical anomaly reported

## 3. Recommended test suites

### Targeted Sprint 2 suites

```bash
docker compose run --rm backend python manage.py test tests.tests.RawNormalizationTests
docker compose run --rm backend python manage.py test tests.tests.EmploiTunisieScraperStructuredParsingTests
docker compose run --rm backend python manage.py test tests.tests.OpportunityTextEnrichmentTests
docker compose run --rm backend python manage.py test tests.tests.OpportunityMaterializationTests
docker compose run --rm backend python manage.py test tests.tests.OpportuniteAPITests
docker compose run --rm backend python manage.py test tests.tests.PipelineTests
```

### Extended regression suites

```bash
docker compose run --rm backend python manage.py test tests.test_scrapers
docker compose run --rm backend python manage.py test tests.test_linkedin_scraper
docker compose run --rm backend python manage.py test tests.tests_quality
docker compose run --rm backend python manage.py test tests.tests_embeddings
docker compose run --rm backend python manage.py test tests.tests_marchespublics
docker compose run --rm backend python manage.py test tests.test_nlp_preprocessing
```

### Full backend validation pass

```bash
docker compose run --rm backend python manage.py test tests.tests tests.test_scrapers tests.test_linkedin_scraper tests.tests_quality tests.tests_embeddings tests.tests_marchespublics tests.test_nlp_preprocessing
```

## 4. Data quality spot checks

### EmploiTunisie source URL completeness

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); print({'null': qs.filter(source_item_url__isnull=True).count(), 'empty': qs.filter(source_item_url='').count()})"
```

### EmploiTunisie critical field coverage

```bash
docker compose run --rm backend python manage.py shell -c "from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); print({'organisation_empty': qs.filter(organisation_nom='').count(), 'ville_empty': qs.filter(ville='').count(), 'contract_empty': qs.filter(contract_type='').count(), 'description_html_empty': qs.filter(description_html='').count()})"
```

### EmploiTunisie structured experience and skills coverage

```bash
docker compose run --rm backend python manage.py shell -c "from django.db.models import Q; from opportunities.models import Opportunite; qs=Opportunite.objects.filter(source__nom__iexact='EmploiTunisie'); total=qs.count(); exp=qs.filter(Q(experience_min__isnull=False) | Q(experience_max__isnull=False)).count(); skills=qs.exclude(skills=[]).count(); print({'total': total, 'with_experience_bounds': exp, 'with_skills': skills})"
```

## 5. API endpoints to verify

- `GET /api/opportunities/`
- `GET /api/opportunities/{id}/`
- `GET /api/opportunities/{id}/similar/?k=5`
- `GET /api/sources/`
- `GET /api/metrics/pipeline/` (authenticated)

Example curl calls:

```bash
curl -X GET http://localhost:8000/api/opportunities/
curl -X GET http://localhost:8000/api/opportunities/<ID>/
curl -X GET "http://localhost:8000/api/opportunities/<ID>/similar/?k=5"
curl -X GET http://localhost:8000/api/sources/
curl -X GET http://localhost:8000/api/metrics/pipeline/ -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## 6. Release sign-off checklist

Sprint 2 is ready for release when:
- collection runs without blocking errors,
- raw backlog stays under control,
- targeted Sprint 2 tests pass,
- dataset metrics remain coherent,
- list/detail/similar API endpoints respond correctly,
- docs match the current code paths and test modules.
