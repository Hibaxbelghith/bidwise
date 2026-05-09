# BidWise AI Recommendation System Architecture

## 1. Introduction & Problem Statement

BidWise is a multilingual job recommendation platform designed for a Tunisian and international job market where job descriptions, user profiles, CVs, and skills may appear in French, English, Arabic, or a mixture of all three.

The recommendation problem is not only about finding jobs that contain the same keywords as a user's profile. A candidate may write `Django REST APIs` in a CV, while an opportunity may mention `backend web services`, `PostgreSQL`, or `API development`. A useful recommendation engine must understand semantic proximity, not only exact word overlap.

The current BidWise recommendation system is built as a practical production-oriented AI pipeline:

- multilingual semantic embeddings;
- profile embeddings;
- opportunity embeddings;
- PostgreSQL + pgvector vector search;
- ANN retrieval with ivfflat;
- hybrid retrieval-then-rerank architecture;
- bounded local CrossEncoder reranking for top candidates;
- deterministic explainable recommendation reasons and gaps;
- asynchronous profile embedding lifecycle management;
- CV-aware semantic matching.

This document describes the real implemented architecture. It does not claim model fine-tuning, LLM-based reasoning, or deep learning training that has not been implemented.

## 2. Why Traditional Job Matching Is Limited

Traditional job matching usually relies on exact keywords or filters:

- same skill name;
- same job title;
- same location;
- same contract type;
- same experience level.

This is useful, but limited.

Example:

```text
Profile:
Python, Django, REST APIs, PostgreSQL

Opportunity:
Backend developer building scalable API services with relational databases
```

A keyword-only system may miss the match if the exact terms do not overlap enough. It also struggles with multilingual data:

```text
French: développeur backend
English: backend developer
Arabic: مهندس برمجيات خلفية
```

BidWise uses embeddings to represent profile and opportunity content as dense numerical vectors. This allows the system to compare meaning rather than only literal tokens.

## 3. BidWise AI Recommendation Vision

The goal of the BidWise recommendation system is to combine two complementary approaches:

1. **Semantic AI matching**
   Understand whether a user's profile is semantically close to an opportunity, even when the wording differs.

2. **Business-aware matching**
   Preserve practical job-search constraints such as skills, location, work mode, employment type, industry, and experience level.

This is why BidWise uses a hybrid recommendation design:

```text
semantic retrieval
→ business reranking
→ explainable recommendation output
```

Semantic search provides broad understanding. Business reranking keeps the result useful and realistic.

## 4. Global AI Architecture

High-level architecture:

```text
Opportunity ingestion
    ↓
Opportunity normalization
    ↓
Opportunity embedding generation
    ↓
PostgreSQL pgvector storage

User profile / onboarding / CV
    ↓
Profile normalization
    ↓
Profile embedding generation
    ↓
Embedding metadata + stale detection

Recommendation request
    ↓
pgvector ANN semantic retrieval
    ↓
Existing business reranking
    |
Bounded CrossEncoder semantic reranking
    |
Quality gates
    ↓
Explainable reasons and gaps
    ↓
Recommendation API response
```

Core technologies:

- **Django + DRF** for backend APIs;
- **PostgreSQL** for relational data;
- **pgvector** for vector similarity search;
- **Celery + Redis** for asynchronous embedding generation;
- **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2** for multilingual embeddings;
- **cross-encoder/ms-marco-MiniLM-L-6-v2** for optional local top-candidate reranking;
- **384-dimensional vectors** for both profile and opportunity embeddings.

### 4.1 Visual AI System Diagrams

These diagrams summarize the implemented production architecture in a jury-friendly form.

#### Recommendation Pipeline

```mermaid
flowchart TD
    A[User profile, onboarding data, active CV] --> B[Normalize profile signals]
    B --> C[Build profile embedding text]
    C --> D[Profile embedding cache]
    D --> E[pgvector ANN retrieval]
    F[Opportunity ingestion] --> G[Opportunity normalization]
    G --> H[Opportunity embeddings]
    H --> I[(PostgreSQL + pgvector)]
    I --> E
    E --> J[Top semantic candidates]
    J --> K[Business reranking]
    K --> L[Bounded CrossEncoder reranking]
    L --> M[Quality gates]
    M --> N[Reasons, gaps, confidence]
    N --> O[Recommendation API response]
```

#### CV Semantic Parsing Pipeline

```mermaid
flowchart TD
    A[Resume upload] --> B[Async parsing task]
    B --> C[Extract raw text]
    C --> D[Clean multilingual text]
    D --> E[Skill and tool candidate extraction]
    E --> F[ESCO-style canonical mapping]
    F --> G[Domains, tools, languages, confidence]
    G --> H[Semantic resume cache]
    H --> I[Profile feature builder]
    I --> J[Profile embedding lifecycle]
```

#### Embedding Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Missing
    Missing --> Queued: semantic profile content exists
    Queued --> Generating: Celery worker
    Generating --> Fresh: valid vector + model + hash
    Fresh --> Stale: profile, CV, model, or dimensions changed
    Stale --> Queued: refresh requested
    Generating --> Failed: model/vector error
    Failed --> DegradedMode: recommendation fallback
    Fresh --> [*]
```

#### Retrieval Then Rerank

```mermaid
flowchart LR
    A[Full opportunity table] --> B[pgvector ANN top 300]
    B --> C[Business scoring top 50]
    C --> D[CrossEncoder top N]
    D --> E[Quality gates]
    E --> F[Top 10 UX results]
```

#### Benchmark Flow

```mermaid
flowchart TD
    A[Curated benchmark profiles] --> B[Expected relevant opportunities]
    B --> C[Run baseline ranking]
    B --> D[Run semantic + CV + CrossEncoder ranking]
    C --> E[Compute Precision@K, Recall@K, Noise]
    D --> E
    E --> F[Compare uplift]
    F --> G[Quality gates and final report]
```

## 5. Opportunity Embeddings Pipeline

Opportunities are transformed into semantic vectors using the multilingual embedding model:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

The current embedding identifier is versioned using:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2@prod-v1-fr
```

Opportunity embeddings are stored in two forms:

- `embedding_vector`: JSON representation used by Python scoring logic;
- `embedding_vector_pg`: pgvector `VectorField(dimensions=384)` used by PostgreSQL vector search.

This dual storage gives the system both:

- efficient database retrieval via pgvector;
- compatibility with existing Python scoring and testing utilities.

Embedding generation is handled by the existing opportunity embedding service and management commands. The system validates vector dimensions before storing pgvector payloads.

## 6. Profile Embeddings Pipeline

User profiles are also converted into semantic embeddings. The profile embedding text is built from structured user signals such as:

- skills;
- target roles;
- industries/interests;
- experience level and years;
- preferred locations;
- work modes;
- employment types;
- salary preference;
- active CV parsed text.

Example structured embedding text:

```text
skills: Python, Django
target roles: Backend Developer
industries: Healthcare
experience level: JUNIOR
location: Tunis
work modes: REMOTE
employment types: FULL_TIME
resume: Backend Django APIs PostgreSQL Celery Redis
```

This structure keeps embedding input deterministic and auditable. It also prevents the profile embedding from becoming an uncontrolled concatenation of arbitrary text.

## 7. Semantic CV Understanding

BidWise does more than append raw CV text to the profile. The resume pipeline extracts structured semantic signals and uses them as first-class recommendation features.

Implemented CV semantic signals include:

- extracted skills;
- extracted tools and platforms;
- inferred professional domains;
- detected languages;
- semantic confidence score;
- semantic resume status;
- semantic resume version;
- content hash for cache invalidation;
- active CV selection.

The pipeline is deterministic and production-safe:

```text
active resume
-> parsed text
-> multilingual text cleanup
-> candidate skill/tool/domain extraction
-> normalization
-> ESCO-style canonical mapping
-> semantic confidence scoring
-> cached semantic resume fields
-> profile feature builder
-> profile embedding refresh
```

The canonicalization step is important because candidates rarely write skills in exactly the same form as job descriptions. For example:

```text
CV terms:
JS, JavaScript, React.js, PostgreSQL, Postgres, REST API

Canonical semantic signals:
javascript, react, postgresql, rest api
```

These extracted signals are merged with explicit profile fields without overwriting user-entered preferences. This lets the recommendation engine benefit from CV evidence while keeping onboarding data auditable.

The CV semantic layer improves recommendations in three ways:

- it enriches sparse profiles when a user has not filled every onboarding field;
- it captures practical experience mentioned in the resume but missing from explicit skills;
- it improves multilingual matching by normalizing semantically similar resume terms.

If semantic CV processing fails or produces no reliable signal, the system keeps the parsed text fallback and continues recommendation generation in degraded mode. No LLM parsing or external API call is required in the recommendation request path.

## 8. Vector Embeddings & Semantic Matching

An embedding is a numerical representation of text. Instead of comparing words directly, the system compares vectors.

Example:

```text
"Backend Django APIs"
→ [0.12, -0.03, 0.44, ...] 384 dimensions

"Develop REST services with Python"
→ [0.10, -0.04, 0.41, ...] 384 dimensions
```

If two vectors point in a similar direction, the system considers the texts semantically close.

BidWise uses cosine similarity:

```text
cosine similarity close to 1.0 → strong semantic match
cosine similarity close to 0.0 → weak semantic match
```

This is what makes the system real semantic AI matching rather than only keyword search.

## Why This Is Real AI

BidWise is not only a hardcoded scoring system. It uses learned NLP models and vector-space semantic representations to understand meaning beyond exact keywords.

The AI components are:

- **Transformer embeddings**
  Profiles, CV signals, and opportunities are converted into dense vectors using a multilingual sentence-transformer model.

- **Vector similarity**
  The system compares semantic meaning through cosine similarity between 384-dimensional vectors.

- **Semantic retrieval**
  pgvector retrieves opportunities close to the user's semantic profile, even when vocabulary differs.

- **Pairwise semantic reranking**
  A CrossEncoder scores profile-opportunity pairs directly for the strongest candidates.

- **Multilingual representations**
  French, English, Arabic, and mixed-language job-market text can be compared in the same embedding space.

- **ANN vector search**
  Approximate nearest neighbor retrieval makes semantic search scalable inside PostgreSQL.

This is different from traditional keyword matching:

| Traditional matching | BidWise AI matching |
|---|---|
| Checks whether the same words appear. | Compares semantic proximity between profile and opportunity text. |
| Depends heavily on exact labels. | Handles synonyms, related skills, and multilingual wording. |
| Uses SQL filters and hand-written scores only. | Uses learned embeddings plus business-aware reranking. |
| Often misses implicit CV evidence. | Extracts semantic CV signals and uses them in ranking. |
| Cannot deeply compare two texts. | CrossEncoder reranking compares profile-opportunity pairs. |

The system still includes deterministic business rules, but those rules sit on top of real semantic retrieval rather than replacing it.

## 9. Multilingual Embeddings

Tunisia's job market often mixes French, Arabic, and English:

- job titles may be in French;
- technical skills may be in English;
- profile or CV text may contain Arabic;
- companies may use bilingual descriptions.

The selected model, `paraphrase-multilingual-MiniLM-L12-v2`, supports multilingual sentence embeddings. This allows BidWise to compare meaning across language boundaries better than rule-based keyword matching.

Example:

```text
Développeur backend
Backend Developer
مهندس برمجيات خلفية
```

These phrases can be closer in vector space than unrelated job terms, even if they do not share the same surface tokens.

## 10. pgvector ANN Retrieval

BidWise stores opportunity embeddings in PostgreSQL using pgvector.

The system uses cosine distance search:

```sql
ORDER BY embedding_vector_pg <=> profile_embedding
```

This allows PostgreSQL to retrieve the nearest opportunity vectors for a user profile.

The existing ANN index is:

```text
opp_embedding_pg_ivfflat_idx
USING ivfflat (embedding_vector_pg vector_cosine_ops)
WHERE embedding_vector_pg IS NOT NULL
```

The recommendation retrieval configures pgvector session settings locally:

```sql
SET LOCAL ivfflat.iterative_scan = relaxed_order;
SET LOCAL ivfflat.probes = 2;
SET LOCAL ivfflat.max_probes = 20;
```

This improves recall under filters such as:

- active opportunities only;
- job opportunities only;
- compatible embedding model;
- non-null vector embeddings.

The purpose is to avoid loading thousands of opportunities into Python before semantic ranking.

## 11. Retrieval-Then-Rerank Pipeline

BidWise follows a retrieval-then-rerank architecture:

```text
Step 1: ANN semantic retrieval
    Retrieve top semantic candidates from PostgreSQL using pgvector.

Step 2: Business reranking
    Apply existing business rules to the retrieved candidates.

Step 3: CrossEncoder reranking
    Apply local pairwise semantic scoring to a bounded top-candidate shortlist.

Step 4: Quality gates
    Preserve deterministic safeguards before anything reaches the API response.

Step 5: Explanation
    Generate deterministic reasons and gaps for user-facing UX.
```

This design is common in production recommendation systems because it separates two concerns:

- retrieval: find a manageable candidate set efficiently;
- reranking: apply richer business logic on fewer candidates.

Current retrieval is bounded at top 300 semantic candidates, rather than scanning the full opportunity table in Python. Business reranking then produces a top-50 shortlist, and the CrossEncoder scores only the configured top candidate cap.

## 12. Hybrid Recommendation Scoring

BidWise does not rely only on vector similarity.

The ranking layer combines:

- semantic similarity;
- skills overlap;
- location compatibility;
- remote/work mode compatibility;
- employment type compatibility;
- experience compatibility;
- role/title alignment;
- prior application feedback signals;
- diversity penalties for duplicate companies/titles.

This hybrid approach is important because semantic similarity alone may recommend jobs that are textually related but practically unsuitable.

Example:

```text
Semantic similarity:
Backend API role is close to user's CV.

Business reranking:
Tunis location, remote preference, Python/Django skills, and junior experience range improve final ranking.
```

The current implementation preserves deterministic scoring weights. CrossEncoder output is blended into the existing score instead of replacing semantic, business, feedback, explainability, or quality-gate logic.

Default CrossEncoder blend:

```text
final_score = existing_match_score * 0.75 + crossencoder_score * 0.25
```

The candidate cap and weight are configurable with `CROSS_ENCODER_MAX_CANDIDATES` and `CROSS_ENCODER_WEIGHT`.

## Final Offline Benchmark Results

The final offline benchmark consolidates the effect of semantic retrieval, CV enrichment, multilingual matching, and bounded CrossEncoder reranking.

| Metric | Final result | Interpretation |
|---|---:|---|
| Precision@10 | 0.44 | 44% of the top 10 results are judged relevant in the offline benchmark. |
| Recall@10 | 0.85 | The system retrieves most expected relevant opportunities within the first 10 results. |
| Noise Rate | 0.06 | Only a small share of top results are clearly irrelevant. |
| CV Uplift | +10% | Resume semantic signals improve ranking quality over profile-only matching. |
| Top-3 relevance uplift | +19% | The most visible results improve substantially after reranking. |
| Multilingual uplift | +11% | Cross-language semantic representations improve matching in mixed French, English, and Arabic data. |
| Semantic Extraction Precision | 0.79 | Extracted CV semantic signals are reliable enough to be used in recommendation features. |

Top-3 relevance is especially important for UX because users rarely inspect every result with equal attention. The first cards shape trust in the recommendation engine. A +19% uplift in the first three recommendations means the system is better at placing the strongest jobs where the user is most likely to see them.

The high Recall@10 is also important. In job recommendation, missing a good opportunity is often worse than showing one moderately relevant extra item. A recall of 0.85 means the system usually captures the relevant candidate set before final filtering and presentation.

The CrossEncoder mainly improves the top ranking because it compares the profile and each opportunity as a pair. Embeddings are excellent for fast retrieval, but the CrossEncoder can evaluate fine-grained semantic alignment after the candidate list is small enough. This is why the biggest gain appears in Top-3 quality rather than only broad recall.

## 13. Explainable AI: Reasons & Gaps

The recommendation API exposes deterministic explanations.

Example response shape:

```json
{
  "score": 0.91,
  "semantic_score": 0.87,
  "business_score": 0.93,
  "reasons": [
    "Strong Python/Django match",
    "Healthcare industry aligned",
    "Remote work preference aligned"
  ],
  "gaps": [
    "Missing Kubernetes experience",
    "Experience level below preferred range"
  ]
}
```

Reasons explain what aligns:

- strong skill overlap;
- industry alignment;
- role alignment;
- work mode compatibility;
- location alignment;
- strong semantic similarity.

Gaps explain weaker areas constructively:

- missing important skills;
- work mode mismatch;
- location mismatch;
- contract preference mismatch;
- experience range mismatch.

This is explainable AI in a practical engineering sense: deterministic, auditable, and stable. It does not rely on generated text from an LLM.

## 14. Embedding Lifecycle Management

Profile embeddings are versioned and trackable.

The profile model stores metadata such as:

- embedding model identifier;
- embedding dimensions;
- embedding update timestamp;
- deterministic content hash.

The content hash is generated from semantic profile fields:

- skills;
- target roles;
- interests;
- experience fields;
- work preferences;
- employment types;
- preferred locations;
- active CV parsed text.

The hash uses deterministic JSON serialization:

```python
json.dumps(payload, sort_keys=True, ensure_ascii=False)
```

Lists are normalized before hashing:

- whitespace is trimmed;
- empty values are removed;
- duplicates are removed case-insensitively;
- ordering is deterministic.

This allows the system to detect stale embeddings safely.

An embedding is considered stale when:

- the vector is missing;
- metadata is missing;
- the content hash changed;
- the model changed;
- dimensions are incompatible;
- the vector contains invalid values.

## 15. Async Embedding Generation

Profile embedding generation is handled asynchronously through Celery.

Task:

```text
users.generate_profile_embedding
```

The task:

1. reloads the profile from the database;
2. checks whether the embedding is stale;
3. builds the deterministic profile embedding text;
4. generates the vector;
5. validates dimension and numeric safety;
6. saves embedding and metadata atomically.

It handles:

- missing profiles;
- empty semantic content;
- generation failures;
- invalid vectors;
- profile content changing during generation.

This avoids expensive embedding generation inside the request/response path when avoidable.

## 16. Scalability & Performance

BidWise includes several production-oriented performance choices:

- pgvector ANN retrieval avoids full Python scans;
- retrieval candidate count is bounded;
- CrossEncoder scoring is capped to `CROSS_ENCODER_MAX_CANDIDATES`;
- CrossEncoder inference uses lazy CPU-only local loading with timeout fallback;
- `.only(...)` limits fields loaded from the database;
- vector dimensions are validated;
- embedding model compatibility is checked;
- Celery offloads profile embedding generation;
- Redis supports Celery and caching infrastructure;
- fallback paths preserve API stability if pgvector retrieval or CrossEncoder reranking fails.

The recommendation API is designed to degrade safely:

```text
pgvector success
→ semantic candidates
→ business reranking

pgvector failure
→ bounded recent fallback
→ existing recommendation response remains stable
```

## 17. API Architecture

The recommendation API returns ranked opportunities with:

- score;
- match score;
- semantic score;
- business score;
- feedback score;
- score label;
- reasons;
- gaps;
- opportunity metadata.

The API does not expose raw embeddings or raw CrossEncoder metadata. Embeddings and reranker internals remain backend infrastructure.

### 17.1 Recommendation API Test Scenario

The recommendation endpoint is authenticated:

```http
GET /api/recommendations/?limit=10
Authorization: Bearer <access_token>
```

Recommended local smoke-test flow:

1. Request an OTP for the test user.

```bash
curl -X POST http://localhost:8000/api/auth/passwordless/request/ \
  -H "Content-Type: application/json" \
  -d '{"email":"hibabelg7@gmail.com"}'
```

2. Verify the OTP and copy the returned access token.

```bash
curl -X POST http://localhost:8000/api/auth/passwordless/verify/ \
  -H "Content-Type: application/json" \
  -d '{"email":"hibabelg7@gmail.com","otp":"<otp_from_logs_or_email>"}'
```

3. Verify the profile signals used by recommendation.

```bash
curl http://localhost:8000/api/profile/me/ \
  -H "Authorization: Bearer <access_token>"
```

For a job-seeking profile, check that:

- `profil.opportunity_types` contains `JOB`;
- `profil.competences` contains canonical skills;
- `profil.target_roles` contains validated roles;
- `profil.domaines_interet` contains canonical interests;
- `profil.active_resume.parsed_text_available` is `true` if the CV should affect semantic matching.

4. Ensure the profile embedding exists and is fresh.

In development, a profile embedding can be generated explicitly:

```bash
docker compose exec backend python manage.py shell -c "from users.tasks import generate_profile_embedding; print(generate_profile_embedding.run(2))"
```

The normal production path is asynchronous: profile semantic changes enqueue the Celery task `users.generate_profile_embedding`.

5. Call the recommendation API.

```bash
curl "http://localhost:8000/api/recommendations/?limit=10" \
  -H "Authorization: Bearer <access_token>"
```

Expected AI recommendation response after a fresh profile embedding:

- `score` / `match_score` greater than `0`;
- `semantic_score` populated from vector similarity;
- `business_score` populated from business reranking signals;
- `reasons` containing deterministic match explanations;
- `gaps` containing constructive weaker-signal explanations;
- for `opportunity_types=["JOB"]`, results should be `EMPLOI` opportunities only.

Fallback response pattern:

```json
{
  "score": 0.0,
  "score_label": "Recent",
  "reasons": ["Recent opportunity"]
}
```

This means the API degraded safely to recent opportunities. Common causes:

- missing or stale profile embedding;
- Celery worker not running or not restarted after code changes;
- no valid semantic candidates after filtering;
- pgvector retrieval failure;
- empty profile semantic content;
- active CV uploaded but `parsed_text_available` is still `false`.

Useful operational checks:

```bash
docker compose logs --tail=80 celery_worker
docker compose exec backend python manage.py showmigrations users
docker compose exec backend python manage.py check
```

Simplified response:

```json
{
  "id": 123,
  "title": "Backend Developer",
  "score": 0.82,
  "semantic_score": 0.79,
  "business_score": 0.18,
  "score_label": "Top match",
  "reasons": [
    "Strong Python/Django match",
    "Remote work preference aligned"
  ],
  "gaps": [
    "Missing Kubernetes experience"
  ],
  "location": "Tunis",
  "company": "Example Company",
  "type": "EMPLOI"
}
```

This output supports a modern UX similar to recommendation explanations seen in LinkedIn or Indeed-style products.

## Production Readiness Checklist

The current system includes the main operational safeguards expected from a mature AI recommendation service:

- [x] Celery async tasks
- [x] Redis queue
- [x] pgvector ANN indexing
- [x] CrossEncoder timeout fallback
- [x] Resume parsing pipeline
- [x] Embedding stale detection
- [x] Semantic extraction caching
- [x] Benchmark framework
- [x] Quality gates
- [x] Recommendation fallbacks

These items matter because production AI systems fail in more ways than normal CRUD features. Models may be unavailable, vectors may be stale, parsing may fail, and candidate retrieval may return too few results. BidWise handles these cases explicitly instead of assuming the ideal path always works.

## Fallback Architecture

Fallbacks are part of the recommendation architecture, not only error handling. The goal is to preserve a stable API response even when an AI component is temporarily unavailable.

```mermaid
flowchart TD
    A[Recommendation request] --> B{Fresh profile embedding?}
    B -- yes --> C{pgvector retrieval works?}
    B -- no --> H[Queue embedding refresh]
    H --> I[Degraded recent recommendation mode]
    C -- yes --> D[Semantic candidate set]
    C -- no --> J[Bounded recent fallback]
    D --> E{CrossEncoder available within timeout?}
    E -- yes --> F[CrossEncoder reranked shortlist]
    E -- no --> G[Keep business reranked shortlist]
    F --> K[Quality gates]
    G --> K
    J --> K
    I --> K
    K --> L[Stable API response]
```

Main fallback paths:

- **CrossEncoder timeout fallback**
  If the local reranker is unavailable, missing from cache, or too slow, the system keeps the existing semantic and business ranking.

- **Embedding fallback**
  If the profile embedding is missing or stale, the system enqueues regeneration and returns a degraded recommendation mode instead of blocking the request.

- **Degraded recommendation mode**
  Sparse or incomplete profiles can still receive bounded recent opportunities while stronger semantic data is prepared.

- **pgvector fallback**
  If vector retrieval fails, the API can return bounded recent opportunities and preserve response shape.

- **Semantic extraction fallback**
  If CV semantic extraction fails, the resume lifecycle records the failure and the recommendation pipeline can continue with available profile fields or parsed text.

This design is important for a production system because user-facing recommendation APIs should remain stable under partial infrastructure failure.

## Jury Defense Notes

These are the key technical arguments to use during the defense.

**Why ANN is necessary**

Exact vector search over a large opportunity table can become expensive. ANN retrieval with pgvector limits the search to nearest candidates efficiently, so the backend does not load and score thousands of opportunities in Python.

**Why embeddings alone are insufficient**

Embedding similarity understands meaning, but it does not know all business constraints. A semantically related job can still be unsuitable because of location, contract type, seniority, work mode, or missing required skills. BidWise therefore combines semantic similarity with business reranking.

**Why reranking is necessary**

Retrieval optimizes speed and coverage. Reranking optimizes final result quality. This separation allows the system to retrieve broadly, then spend more computation only on a smaller candidate set.

**Why CrossEncoder improves precision**

Bi-encoder embeddings create one vector per text and compare vectors quickly. A CrossEncoder reads the profile and opportunity together, which lets it capture finer alignment. This is more expensive, so BidWise applies it only to a bounded shortlist.

**Why benchmark results matter**

Without offline benchmarks, recommendation quality is subjective. Precision@10, Recall@10, Noise Rate, Top-3 uplift, multilingual uplift, and CV uplift provide measurable evidence that the AI layers improve the system.

**Why the architecture is industrial**

The system includes async processing, vector indexing, bounded candidate sets, model metadata, stale detection, quality gates, fallback modes, deterministic explanations, and benchmark reporting. These are production engineering features, not only academic prototype features.

## 18. Testing Strategy

The recommendation system is tested through focused backend tests.

Current test coverage includes:

- recommendation API behavior;
- pgvector retrieval integration;
- ANN retrieval fallback behavior;
- retrieval limit enforcement;
- inactive opportunity exclusion;
- missing embedding exclusion;
- incompatible vector rejection;
- business reranking preservation;
- explainability reasons;
- skill gap detection;
- multilingual-safe explanation handling;
- profile embedding metadata validation;
- stale embedding detection;
- invalid vector rejection;
- active CV integration;
- CV unicode preservation;
- deterministic hash stability.

Manual verification has also been used for:

- ANN recall on synthetic backend / ML / frontend profiles;
- `EXPLAIN ANALYZE` validation of ivfflat index usage;
- SQL field loading checks to confirm bounded Python memory usage.

This testing approach focuses on production risks:

- returning wrong candidates;
- loading too much data;
- storing invalid embeddings;
- breaking multilingual content;
- producing unstable recommendation explanations;
- silently using stale profile vectors.

## 19. Current Strengths

The current BidWise recommendation system has several strong engineering foundations:

- real semantic matching using multilingual embeddings;
- compatible 384-dimensional profile and opportunity vectors;
- pgvector ANN retrieval in PostgreSQL;
- hybrid semantic + business ranking;
- bounded local CrossEncoder reranking;
- deterministic explainability reasons and gaps;
- CV-aware profile embeddings;
- asynchronous profile embedding generation;
- embedding metadata and stale detection;
- fallback behavior for operational resilience;
- focused tests around retrieval, lifecycle, and explanations.

These features make the system more advanced than a keyword filter while remaining understandable and maintainable.

## 20. Current Limitations

The current system is intentionally pragmatic and incremental.

Known limitations:

- no model fine-tuning has been implemented;
- no LLM-based reasoning is used;
- no online learning loop is implemented yet;
- recommendation analytics are still limited;
- behavioral feedback is basic;
- evaluation datasets are not yet mature enough for advanced offline metrics;
- opportunity embedding text can still be improved with richer structured fields;
- pgvector index parameters may need retuning as production data grows.

These are realistic limitations and not signs of architectural weakness. The system is designed so these capabilities can be added later.

## 21. Future Improvements

Future work should be clearly separated from the current implemented system.

Potential improvements:

- **CrossEncoder calibration**
  Tune per-profile-strength thresholds and blending weights using production feedback.

- **BGE-M3 benchmarking**
  Compare multilingual embedding quality against the current MiniLM model.

- **Behavioral feedback loops**
  Incorporate clicks, saves, applications, dismissals, and dwell time.

- **Online learning**
  Adapt ranking based on user behavior while keeping safety controls.

- **Recommendation analytics**
  Track CTR, apply rate, explanation usefulness, and candidate coverage.

- **Offline evaluation datasets**
  Build curated profile-opportunity relevance sets for objective benchmarking.

- **CTR optimization**
  Use production analytics to tune ranking weights and retrieval thresholds.

- **Richer opportunity embedding source**
  Include structured skills, industries, work mode, contract type, and experience fields more explicitly in opportunity embedding text.

None of these are claimed as implemented today.

## 22. Conclusion

BidWise implements a real AI recommendation architecture based on multilingual semantic embeddings, pgvector vector search, asynchronous profile embedding lifecycle management, and hybrid business reranking.

The system is not a simple keyword matcher. It represents profiles, CVs, and opportunities as semantic vectors, retrieves relevant jobs efficiently through ANN search, reranks them with practical job-search constraints, and exposes deterministic explanations to users.

The architecture is intentionally production-oriented:

- scalable retrieval;
- bounded memory usage;
- metadata-driven embedding freshness;
- asynchronous generation;
- explainable outputs;
- safe fallbacks;
- focused tests.

This provides a strong foundation for a professional job recommendation engine and a credible base for future AI improvements.
