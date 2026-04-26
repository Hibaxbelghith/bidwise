# BidWise

BidWise is an opportunity intelligence platform that collects heterogeneous sources, turns them into a normalized dataset, and exposes them to web and mobile clients with recommendation-ready signals.

## Project vision

BidWise is built around one core product principle: separate raw acquisition from business intelligence. The raw layer stays replayable and auditable, while the canonical layer stays clean enough for filtering, ranking, and future AI features.

The platform targets jobs, internships, tenders, and other opportunity flows that need:
- reliable ingestion,
- deterministic normalization,
- quality-controlled materialization,
- cross-client delivery,
- similarity and personalization primitives.

## Current status

- Sprint 1 complete: passwordless auth, Google Sign-In, onboarding, JWT rotation/blacklist, suspicious login protection.
- Sprint 2 complete: end-to-end opportunities pipeline delivered from scraping to API and similarity.
- Sprint 3 next: profile-driven ranking, save/apply workflow, and generative candidate assistance.

## System architecture

### Backend pipeline

`Scraper -> RawOpportunite -> normalization -> enrichment -> quality gate -> materialization -> Opportunite -> embeddings -> similarity -> DRF API`

Main backend modules:
- `backend/opportunities/scraping/pipeline.py`
- `backend/opportunities/normalization/service.py`
- `backend/opportunities/enrichment/text_enrichment.py`
- `backend/opportunities/quality/quality_gate.py`
- `backend/opportunities/materialization/service.py`
- `backend/opportunities/similarity.py`

### Client apps

- `frontend/`: React + Vite web client for browse, detail, auth, onboarding, dashboard, and profile flows.
- `bidwise-mobile/`: Expo Router mobile client organized with `src/features/*` and `src/shared/*`.

## Implemented features

- Multi-source ingestion with raw snapshot persistence and replay-safe processing.
- Active source connectors in code for Keejob, EmploiTunisie, LinkedIn public listings, and MarchesPublics.
- Deterministic normalization for dates, city canonization, contract types, education levels, URLs, and experience ranges.
- Text enrichment for salary recovery, skills extraction, language fallbacks, and structured field completion.
- Quality scoring and lightweight quality gating before user-facing materialization.
- Canonical materialization with non-destructive merge rules and duplicate-safe identity keys.
- Opportunity browse/detail API with filtering, pagination, legacy route compatibility, and source listing.
- Embedding generation plus similarity ranking with optional pgvector acceleration and Python fallback.
- Web and mobile clients consuming the same API surface.

## Repository layout

```text
backend/
  config/
  opportunities/
  users/
  applications/
  notifications/
frontend/
bidwise-mobile/
docker/
```

## Running locally

### 1. Backend and database

Create a root `.env` with at least:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DB_NAME=bidwise
DB_USER=bidwise
DB_PASSWORD=bidwise
DB_HOST=db
DB_PORT=5432
```

Optional integrations:

```env
GOOGLE_CLIENT_ID=
GMAIL_ADDRESS=
GMAIL_APP_PASSWORD=
VITE_API_URL=http://localhost:8000/api
EXPO_PUBLIC_API_BASE_URL=http://<your-lan-ip>:8000/api
OPPORTUNITY_PGVECTOR_ENABLED=false
```

Start the stack:

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
```

API base URL: `http://localhost:8000/api`

### 2. Web client

```bash
cd frontend
npm install
npm run dev
```

### 3. Mobile client

```bash
cd bidwise-mobile
npm install
npx expo start
```

## Useful pipeline commands

```bash
docker compose run --rm backend python manage.py collect_opportunities --source keejob
docker compose run --rm backend python manage.py collect_opportunities --source emploitunisie
docker compose run --rm backend python manage.py shell -c "from opportunities.processing import process_pending_raw_opportunities; print(process_pending_raw_opportunities(limit=500))"
docker compose run --rm backend python manage.py dataset_metrics
docker compose run --rm backend python manage.py audit_opportunities_dataset
docker compose run --rm backend python manage.py generate_embeddings
```

## API overview

Authentication:
- `POST /api/auth/passwordless/request/`
- `POST /api/auth/passwordless/verify/`
- `POST /api/auth/google/`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`

Opportunity data:
- `GET /api/opportunities/`
- `GET /api/opportunities/{id}/`
- `GET /api/opportunities/{id}/similar/?k=5`
- `GET /api/sources/`
- `GET /api/metrics/pipeline/` (authenticated)

Common filters on `GET /api/opportunities/`:
- `search`
- `type` or `type_opportunite`
- `status` or `statut`
- `city` or `ville`
- `min_salary`
- `source`
- `ordering`

## Testing

Core Sprint 2 test suites live in `backend/tests/`.

```bash
docker compose run --rm backend python manage.py test tests.tests
docker compose run --rm backend python manage.py test tests.test_scrapers tests.test_linkedin_scraper
docker compose run --rm backend python manage.py test tests.tests_quality tests.tests_embeddings tests.tests_marchespublics tests.test_nlp_preprocessing
```

## Sprint 3 focus

- Personalized ranking driven by onboarding/profile signals.
- Save/apply workflow orchestration across clients.
- CV / cover letter assistance and user-facing AI features.
- Production hardening around scheduling, monitoring, and duplicate cleanup.
