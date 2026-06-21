# BidWise - Technical stack overview

Last updated: 2026-06-19

## Purpose

This document summarizes the main technologies and tools used to build BidWise and explains the role of each one. It is designed for academic presentation and project defense.

BidWise is implemented as a full-stack platform with a web frontend, a Django REST backend, PostgreSQL persistence, Dockerized services, asynchronous automation, monitoring, and AI-powered recommendation features.

## High-level architecture

```text
React frontend
  -> Django REST API
  -> PostgreSQL / pgvector
  -> Celery workers + Redis
  -> Scraping, normalization, enrichment, embeddings, notifications
  -> Monitoring, Flower, Discord alerts, admin dashboard
```

## Frontend stack

| Tool | Role in the project |
| --- | --- |
| React | Main web user interface for candidates, organizations, admin views, opportunities browsing, and recommendation screens. |
| Vite | Fast frontend development server and build tool. |
| JavaScript / JSX | Component and page implementation language for the web frontend. |
| CSS / design system components | Responsive layouts, filters, cards, dashboards, and opportunity detail views. |
| Frontend services/hooks | Encapsulate API calls, URL query state, filters, pagination, sorting, and data transformation for UI components. |

Frontend responsibilities:

- display opportunities and details;
- provide search, filters, sorting, and recommendation UI;
- expose dashboards and user workflows;
- consume backend API responses without running scraping logic in the browser.

## Backend stack

| Tool | Role in the project |
| --- | --- |
| Python | Main backend language. |
| Django | Core backend framework, data models, settings, management commands, authentication integration, and admin-oriented services. |
| Django REST Framework | API layer for opportunities, users, recommendations, metrics, and admin dashboard endpoints. |
| Django management commands | Operational entry points for scraping, embeddings, enrichment, and maintenance tasks. |

Backend responsibilities:

- expose REST APIs to the frontend and mobile clients;
- persist canonical business data;
- orchestrate opportunity processing;
- run validation, normalization, enrichment, scoring, materialization, and metrics;
- keep request-time operations fast by delegating heavy work to Celery.

## Database and search stack

| Tool | Role in the project |
| --- | --- |
| PostgreSQL | Main relational database for users, opportunities, raw scraped records, pipeline runs, and application data. |
| pgvector | Stores vector embeddings for semantic similarity and future recommendation features. |
| Django ORM | Safe model access, queries, transactions, filtering, aggregation, and migrations. |
| Database migrations | Version-controlled schema evolution. |

Database responsibilities:

- store raw and canonical opportunity data;
- preserve replayable scraped payloads;
- support filters, sorting, dashboard metrics, and deduplication;
- store embeddings for similarity search.

## Scraping and data pipeline stack

| Tool / Module | Role in the project |
| --- | --- |
| Source scrapers | Collect opportunities from LinkedIn, Keejob, EmploiTunisie, and MarchesPublics. |
| `opportunities/pipeline.py` | Scheduler/orchestrator: chooses sources, applies cadence rules, priorities, stale detection, and dispatch logic. |
| `opportunities/scraping/pipeline.py` | Raw ingestion boundary: stores raw records, computes hashes/fingerprints, and preserves source payloads. |
| `opportunities/processing.py` | Raw-to-canonical processing pipeline. |
| Normalization service | Maps source-specific fields into canonical BidWise fields. |
| Enrichment service | Adds derived fields such as skills, salary signals, languages, and structured metadata. |
| Quality scoring | Scores opportunities based on completeness and usability. |
| Materialization service | Creates or updates canonical `Opportunite` rows with deduplication and safe merge rules. |

Pipeline responsibilities:

- collect external opportunities automatically;
- preserve raw data for audit and replay;
- normalize inconsistent external schemas;
- enrich and score records;
- expose clean canonical opportunities to the product.

## Asynchronous automation stack

| Tool | Role in the project |
| --- | --- |
| Celery | Runs heavy background tasks outside HTTP requests. |
| Celery Beat | Periodically dispatches scraping, monitoring, LLM enrichment, notifications, and maintenance tasks. |
| Redis | Celery broker, result backend, pipeline locks, alert state, and anti-spam metadata. |
| Celery queues | Isolate scraping, LLM enrichment, profile processing, and notifications. |
| Flower | Web UI for observing Celery workers and task execution. |

Main workers:

| Worker | Queue | Role |
| --- | --- | --- |
| `scraping@...` | `celery` | Scraping dispatch, source collection, raw materialization, embeddings, monitoring. |
| `enrichment@...` | `opportunity_enrichment` | Offline LLM enrichment for opportunity skills and metadata. |
| `profile@...` | `profile_resume` | Resume parsing and profile embedding tasks. |
| `notifications@...` | `notifications` | Email and notification delivery. |

Automation responsibilities:

- keep scraping independent from user requests;
- prevent slow AI jobs from blocking scraping;
- retry or skip tasks safely;
- avoid duplicate source runs through Redis locks;
- make the system observable through Flower and logs.

## AI and recommendation stack

| Tool / Module | Role in the project |
| --- | --- |
| Sentence Transformers | Generates multilingual embeddings for opportunities. |
| `paraphrase-multilingual-MiniLM-L12-v2` | Embedding model used for French/English semantic similarity. |
| pgvector / Python fallback | Similarity search using database vector operations or in-memory cosine scoring. |
| NLP extraction helpers | Deterministic extraction of skills, salary signals, languages, and experience hints. |
| Offline LLM enrichment | Optional background enrichment for weak or generic opportunity skills. |

AI responsibilities:

- improve opportunity similarity results;
- support multilingual French/English semantic matching;
- enrich opportunity metadata without slowing down page requests;
- prepare the platform for stronger future recommendations.

## Monitoring and alerting stack

| Tool / Module | Role in the project |
| --- | --- |
| Pipeline monitoring service | Detects stuck runs, stale sources, failures, duration anomalies, and embedding backlog. |
| Admin dashboard API | Exposes KPIs, worker state, source monitoring, data quality, and pipeline health. |
| Flower | Shows Celery workers, active tasks, successful tasks, failed tasks, and runtime state. |
| Docker logs | Operational troubleshooting for backend, workers, Beat, Flower, Redis, and database services. |
| Discord webhook alerts | Sends admin/operator warnings and recovery notifications. |

Monitoring responsibilities:

- prove that the pipeline is alive;
- detect failures before users notice stale data;
- notify administrators through Discord;
- provide evidence for demos and academic defense.

## Dockerization and deployment stack

| Tool | Role in the project |
| --- | --- |
| Docker | Containerizes backend, workers, Redis, PostgreSQL, Flower, and related services. |
| Docker Compose | Defines and starts the local multi-service environment. |
| Environment variables / `.env` | Configure database, Redis, alerts, schedules, scraping limits, LLM settings, and secrets. |
| Service health checks | Ensure Redis and PostgreSQL are ready before dependent services start. |

Docker responsibilities:

- make the project reproducible;
- run backend and background workers consistently;
- isolate infrastructure services;
- simplify demonstration and operational checks.

## Version control and collaboration stack

| Tool | Role in the project |
| --- | --- |
| Git | Tracks source code, documentation, migrations, and configuration changes. |
| GitHub | Remote repository, collaboration, branch management, and project history. |
| Feature branches | Separate development work from stable code. |
| Diffs and commits | Provide traceability for implementation decisions and documentation updates. |

Version control responsibilities:

- preserve implementation history;
- support collaboration and review;
- make changes auditable during development and defense.

## Testing and validation stack

| Tool | Role in the project |
| --- | --- |
| Django test runner | Backend unit and integration tests. |
| pytest | Additional scraper and regression tests. |
| Management command smoke tests | Manual validation of scraping, processing, embeddings, and metrics. |
| Docker smoke checks | Validate that the real service stack starts and runs correctly. |

Testing responsibilities:

- protect scraper parsing behavior;
- validate normalization, enrichment, materialization, and API behavior;
- confirm Celery orchestration and monitoring logic;
- provide repeatable defense scenarios.

## Why this stack is valuable

- Separation of concerns: frontend, API, scraping, AI, and monitoring are isolated.
- Scalability: heavy work runs in Celery instead of HTTP requests.
- Reliability: Redis locks, retries, raw persistence, and idempotent materialization reduce data loss and duplicate processing.
- Observability: Flower, dashboard metrics, logs, and Discord alerts make the system explainable.
- AI readiness: embeddings and semantic similarity create a foundation for recommendation features.
- Maintainability: Docker, Git, migrations, and structured documentation make the project easier to reproduce and defend.

