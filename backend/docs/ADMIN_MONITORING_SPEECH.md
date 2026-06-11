# Admin Monitoring Speech Guide

This document is a soutenance-oriented speaking guide for the BidWise admin
supervision workspace. It explains what each admin monitoring page shows, why
each variable matters, and why the displayed information is reliable rather
than decorative.

The goal is not only to describe the UI, but to defend the engineering logic
behind it:

- what is real-time monitoring
- what is historical analytics
- what is coverage or quality supervision
- what should trigger admin action
- what should not be confused with an incident

## How To Present The Admin Workspace

Suggested introduction:

> In BidWise, the admin dashboard is not a static statistics page. It is split
> into several supervision views. Each view has a clear role: platform overview,
> operational monitoring, source monitoring, scheduler supervision, pipeline
> health, alerts, and analytics. I separated these concerns so the admin can
> distinguish current incidents from historical trends and from data-quality
> indicators.

Key idea to repeat during the defense:

> I intentionally avoided mixing all metrics together. A real monitoring system
> must distinguish runtime health, source freshness, scheduler decisions,
> backlog, and quality coverage.

---

## 1. Global Overview

Route:

`/admin/dashboard`

Purpose:

- give a product-level snapshot of the platform
- show platform growth and usage
- summarize users, applications, and opportunities
- avoid operational details here

Suggested speaking line:

> The Global Overview is the business-facing summary page. It helps the
> administrator understand the scale and recent growth of the platform, without
> mixing in runtime alerts or pipeline incidents.

### Main KPI Cards

#### `Users`

Definition:

- total number of user accounts on the platform

Why it matters:

- shows platform adoption
- useful for business growth tracking

Reliability:

- directly derived from persisted user records

#### `Applications`

Definition:

- total number of recorded candidate applications

Why it matters:

- shows whether opportunities are actually generating activity
- one of the clearest engagement signals

Reliability:

- based on stored application rows, not a UI counter

#### `Opportunities`

Definition:

- total number of materialized opportunities currently stored

Why it matters:

- reflects marketplace depth
- useful to compare with application volume and source activity

Reliability:

- aggregated from persisted opportunities after scraping/materialization or
  organization publication

#### `Applications / User`

Definition:

- average number of applications per platform user

Why it matters:

- more honest than a fake “application rate” percentage
- easier to explain than a percentage with ambiguous denominator

Reliability:

- computed from total persisted applications divided by total persisted users

Suggested speaking line:

> I renamed this metric to `Applications / User` because the previous percentage
> label could be misleading. This version is more interpretable during admin
> supervision and during the defense.

### Platform Growth Chart

Section:

`Platform Growth`

Definition:

- daily evolution of:
  - users
  - applications
  - opportunities

Why it matters:

- shows whether the platform is growing consistently or unevenly
- helps identify whether opportunity ingestion and user activity progress
  together

Reliability:

- built from historical daily aggregates, not hand-entered numbers

Important note:

- this is a trend visualization, not an operational alert

Suggested speaking line:

> This chart is intentionally placed in the overview, not in monitoring,
> because it is for growth reading rather than incident handling.

### Recent Activity

Section:

`Recent Activity`

Variables:

- `Users 7d`
- `Applications 7d`
- `Opportunities 7d`

Why they matter:

- provide short rolling windows
- useful when total values are large and less informative

Reliability:

- computed from recent persisted records using date filters

### Distribution Blocks

#### `Users`

Variables:

- candidates
- organizations
- admins
- suspended

Why they matter:

- explain platform role distribution
- show administrative control, especially suspended accounts

#### `Applications by Status`

Possible values include:

- `Submitted`
- `Under review`
- `Shortlisted`
- `Withdrawn`
- `Applied externally`
- `Reminder saved`

Why it matters:

- shows the real usage of application workflows
- distinguishes direct BidWise applications from external-apply tracking

Reliability:

- status labels are mapped from stored application statuses
- values are sorted by volume for easier reading

#### `Opportunities by Type`

Possible values:

- Jobs
- Stages
- Seasonal jobs
- Calls for tender

Why it matters:

- shows marketplace composition
- important in BidWise because the platform supports both recruitment and
  procurement use cases

---

## 2. Operations Monitoring

Route:

`/admin/dashboard/operations`

Purpose:

- show whether the platform is healthy right now
- separate live operational signals from coverage indicators

Suggested speaking line:

> The Operations Monitoring page is the admin control surface. I split it into
> current runtime signals and quality-coverage signals to avoid mixing runtime
> incidents with long-term readiness indicators.

### Hero Block

Variables:

- global status badge: `Healthy`, `Attention needed`, or `Pipeline running`
- `Active alerts`
- `Last completed run`

Why they matter:

- provide the fastest operational interpretation at a glance

Reliability:

- based on the backend-derived pipeline state, not just frontend heuristics

### Operational Signals

#### `Pipeline Lag`

Variables:

- `New raw backlog`
- `Raw inventory`

Difference:

- `New raw backlog` is a live operational signal
- `Raw inventory` is a stock/volume indicator, not an incident by itself

Why this distinction matters:

- avoids calling every large dataset an operational problem

Reliability:

- backlog is computed from unprocessed recent raw records
- inventory is computed from total raw record count

#### `Active Alerts`

Variables:

- critical alert count
- warning alert count
- optional info alert count
- detailed active alert list

Why it matters:

- this is the shortest route from anomaly detection to admin action

Reliability:

- alerts come from anomaly collection logic, not manual input

Important speaking line:

> An alert here is not a vague KPI. It is a concrete anomaly emitted by the
> monitoring rules, for example a stale source, a failed run, or a scraping
> duration anomaly.

### Coverage Health

Purpose:

- show platform readiness for AI features and media quality
- clearly not presented as a runtime incident panel

#### `AI Readiness`

Variables:

- `Coverage`
- `Missing`
- `pgvector`

Meaning:

- `Coverage`: percentage of opportunities with embeddings
- `Missing`: opportunities still without vectors
- `pgvector`: opportunities indexed for vector search

Why it matters:

- recommendation quality depends on embedding coverage

Reliability:

- derived from stored vector/embedding state

#### `Media Coverage`

Variables:

- `With logo`
- `Placeholder`

Meaning:

- measures the completeness of company branding/media fields

Why it matters:

- improves recommendation cards and trust in scraped opportunities

Reliability:

- based on actual stored logo presence, not assumptions

---

## 3. AI Supervision

Route:

`/admin/dashboard/operations`

Purpose:

- supervise the operational state of the AI modules already used by BidWise
- expose only measurable signals, not artificial "AI accuracy" claims

Suggested speaking line:

> The AI Supervision block does not pretend to measure an abstract intelligence
> score. It tracks concrete signals already stored by the platform: processed
> volume, coverage, confidence when available, warnings, fallbacks, and missing
> embeddings.

### Why this section is reliable

Key design choice:

- I intentionally avoided fake metrics such as global AI accuracy
- every displayed value comes from persisted metadata already produced by the
  real modules

This makes the page defensible because it measures:

- operational coverage
- successful processing volume
- fallback behavior
- warnings and known issues
- readiness of embeddings required by recommendation features

### `Moderation AI`

Variables:

- `Coverage`
- `Decisions`
- `Confidence`
- `Human Overrides`
- `Current issue`

Meaning:

- `Coverage` = organization opportunities with stored LLM moderation over all
  organization-published opportunities
- `Decisions` = distribution of approved, pending review, and rejected outputs
- `Confidence` = average stored moderation confidence, only when the LLM
  provided one
- `Human Overrides` = admin decisions that did not match the stored LLM
  decision, over reviewed moderation cases
- `Current issue` = active fallback or known moderation-side operator message

Why it matters:

- proves that moderation is supervised, not blindly trusted
- shows how often human review still changes an LLM decision
- helps detect provider fallback situations

Reliability:

- based on `extra_data["moderation"]["llm"]` and stored admin moderation
  decisions already persisted on opportunities

### `Opportunity Enrichment`

Variables:

- `Coverage`
- `Applied to Skills`
- `Warnings`
- `Confidence`
- `Current issue`

Meaning:

- `Coverage` = opportunities with stored `llm_enrichment`
- `Applied to Skills` = enrichments that actually updated skill storage
- `Warnings` = enrichments carrying stored validation or quality warnings
- `Confidence` = average stored enrichment confidence
- `Current issue` = operator-facing warning summary when present

Why it matters:

- shows that enrichment is not just enabled, but measurably applied
- helps distinguish between stored enrichment and enrichment that really
  affected matching-relevant fields

Reliability:

- based on stored `extra_data["llm_enrichment"]` fields, not estimated values

### `Resume Semantic AI`

Variables:

- `Coverage`
- `Status Mix`
- `Skipped`
- `Confidence`
- `Current issue`

Meaning:

- `Coverage` = resumes with semantic status `SUCCEEDED` over active resumes
- `Status Mix` = failed, pending, and empty semantic analyses
- `Skipped` = resumes intentionally skipped by the semantic pipeline
- `Confidence` = average stored semantic confidence for successful analyses
- `Current issue` = latest safe operator-facing resume semantic error

Why it matters:

- proves that CV analysis is monitored as a real pipeline step
- highlights whether failures are isolated or systemic
- supports the explanation that candidate profiles are enriched semantically for
  recommendation and matching

Reliability:

- based on persisted resume fields such as `semantic_resume_status`,
  `semantic_resume_confidence`, and `semantic_resume_error`

### `Recommendation Readiness`

Variables:

- `Profile Coverage`
- `Opportunity Coverage`
- `pgvector`
- `JobBERT`
- `Current issue`

Meaning:

- `Profile Coverage` = profiles with stored embeddings over total profiles
- `Opportunity Coverage` = opportunities with stored embeddings over total
  opportunities
- `pgvector` = opportunities indexed in vector form for similarity search
- `JobBERT` = profiles and opportunities with JobBERT embeddings available
- `Current issue` = missing embedding coverage summary

Why it matters:

- directly reflects whether AI recommendation features are ready to operate
- helps explain recommendation quality as a function of embedding coverage

Reliability:

- based on stored embedding fields, not derived heuristics

---

## 4. Sources Monitoring

Route:

`/admin/dashboard/sources`

Purpose:

- supervise each scraping or publishing source independently
- detect source-specific issues without mixing them together

Suggested speaking line:

> This page gives me a per-source operational view. Instead of only saying that
> the pipeline is healthy or degraded globally, it tells me which source is
> healthy, running, stale, or currently affected by an issue.

### Columns

#### `Source`

Meaning:

- source identifier such as `linkedin`, `keejob`, `emploi_tn`, `marches_publics`

#### `Status`

Possible values:

- `Healthy`
- `Running`
- `Degraded`
- `Failed`

Why it matters:

- gives the operator a clear operational state per source

Reliability:

- derived from run freshness, active alerts, running state, and latest run
  outcome

#### `Created · Updated`

Meaning:

- cumulative changed records for the monitored period

Why it matters:

- helps distinguish dead sources from actively changing sources

#### `Change rate`

Meaning:

- share of processed items that changed

Why it matters:

- identifies sources that keep producing meaningful deltas

Important note:

- this is not a health score
- it is a throughput/change signal

#### `Last run`

Variables:

- last completed run time
- average duration

Why it matters:

- useful to spot slow sources or long-running behavior

#### `Current issue`

Meaning:

- currently active warning or failure for this specific source

Why it matters:

- lets the admin immediately understand whether there is a real source problem

Example:

- scraping duration anomaly
- stale source
- failed run

---

## 5. Scheduler Intelligence

Route:

`/admin/dashboard/scheduler`

Purpose:

- explain why each source will run sooner or later
- supervise adaptive scheduling logic

Suggested speaking line:

> This page does not monitor content volume directly. It monitors the scheduler
> logic itself: why a source is accelerated, slowed down, or backed off.

### Summary Metrics

#### `Sources`

- number of supervised sources

#### `High priority`

- sources whose adaptive score justifies a faster cadence

#### `Active issues`

- counts only failure-like states requiring review
- does not count normal stale/cooldown decisions as incidents

Why this is important:

- prevents over-alerting
- avoids treating normal scheduler adaptation as a failure

#### `Next run`

- earliest valid scheduled next run among sources

Reliability improvement:

- if no valid run exists, the UI now shows `not scheduled`
- overdue runs are shown as `due now` or `overdue by ...`

### Per-Source Scheduler Card

Variables:

- final scheduler decision
- decision reason
- next run
- priority score
- badges
- score history
- EMA metrics
- failure rate
- freshness lag
- interval

Why they matter:

- let the admin defend the scheduler as an explainable system
- show that adaptive cadence is based on measurable signals, not hardcoded magic

Examples of decision reasons:

- `HIGH CREATED VOLUME`
- `HIGH UPDATED VOLUME`
- `RECENT FAILURES`
- `NO DATA`

Important reliability point:

> I corrected the fallback state so `NO DATA` is shown honestly as absence of
> scheduler history, instead of pretending to be a normal or stable state.

---

## 6. Pipeline Health

Route:

`/admin/dashboard/pipeline`

Purpose:

- supervise the ingestion pipeline and Celery runtime

Suggested speaking line:

> This page focuses on the ingestion engine itself: pipeline state, backlog,
> and Celery execution context.

### Pipeline Health Block

Variables:

- `Current issue`
- status badge
- `Last run processed`
- `Changed records`
- `Change rate`
- `Last completed run`

Why they matter:

- summarize both current state and latest completed run output

Reliability:

- driven by backend-derived health logic instead of only frontend inference

### Backlog Block

Variables:

- `New raw`
- `Raw total`
- `Missing embeddings`
- `Queue length`

Why they matter:

- show whether the pipeline drains correctly after ingestion

### Celery Monitoring

Variables:

- `Current status`
- `Current issue`
- `Workers`
- `Active tasks`
- `Scheduled`
- `Queue length`
- `Reserved`

Why they matter:

- separate execution/runtime health from content metrics

Reliability:

- based on live Celery inspection
- degrades honestly if inspect is unavailable

---

## 6. Alerts

Route:

`/admin/dashboard/alerts`

Purpose:

- centralize anomaly signals in one page

Typical alerts:

- source stale
- pipeline failure
- scraping duration anomaly
- recovery event

Why it matters:

- this is the page for incident reading, independent of business analytics

Reliability:

- alerts are generated by monitoring rules and anomaly collection logic

---

## 8. Analytics

Route:

`/admin/dashboard/analytics`

Purpose:

- show historical reporting, not live incidents

Suggested speaking line:

> Analytics is intentionally historical. I separated it from runtime monitoring
> so an admin does not confuse past failure counts with current incidents.

### Opportunities by Source

Meaning:

- current opportunity volume grouped by business-relevant sources

Reliability improvement:

- internal benchmark source `BidWise Recommendation Benchmark` is excluded from
  the admin analytics chart so the page remains product-facing

### Pipeline History

Variables:

- `Runs recorded`
- `Runs failed`
- `Average change rate`
- `Run success`

Why they matter:

- help evaluate pipeline performance historically

Important note:

- `Runs failed` is historical, not a live alert
- `Average change rate` is throughput/change reporting, not reliability alone

---

## Reliability Principles Used In The Admin Dashboard

These are the main engineering choices worth emphasizing during soutenance:

### 1. Separation of concerns

I separated:

- platform overview
- live operations monitoring
- per-source supervision
- scheduler explainability
- pipeline runtime health
- historical analytics

This avoids misleading dashboards where everything is mixed together.

### 2. Real anomalies vs business metrics

I made sure that:

- active alerts are operational anomalies
- source status is derived from runs and freshness
- scheduler issues count only true failure-like states
- historical analytics do not pretend to be runtime alerts

### 3. Honest fallback states

When no data exists, the UI says:

- `No data available`
- `No scheduler history yet`
- `Not scheduled`

This is important because a monitoring tool must never invent a healthy-looking
state when information is missing.

### 4. Business-facing wording

I renamed or clarified metrics such as:

- `Applications / User` instead of a misleading percentage
- `Content Change Rate` instead of generic `Change Rate`
- `Current issue` instead of `Last error`

This improves interpretability for both admins and the jury.

---

## Short Speaking Script Per Page

### Global Overview

> This page is the business summary of the platform. It shows scale, growth,
> user distribution, application activity, and opportunity composition.

### Operations Monitoring

> This page is the runtime supervision layer. It separates live operational
> signals from AI and media coverage quality indicators.

### AI Supervision

> This section supervises the AI modules through measurable operational signals:
> coverage, processed volume, warnings, confidence when stored, and readiness
> of embeddings required by recommendation features.

### Sources Monitoring

> This page shows source-by-source health. It tells me not only that something
> is wrong, but exactly which source is affected and why.

### Scheduler Intelligence

> This page explains adaptive scheduling decisions. It proves that source cadence
> is based on measurable signals like activity, freshness, and failures.

### Pipeline Health

> This page focuses on the ingestion engine itself: backlog, latest run output,
> and Celery runtime execution.

### Alerts

> This is the incident page. It centralizes anomaly signals so the admin can act
> quickly.

### Analytics

> This page is historical reporting. It shows long-term pipeline and source
> behavior without confusing it with current operational state.

---

## Final Defense Position

Recommended closing line:

> The admin dashboard was designed not as a decorative BI page, but as a real
> supervision workspace. I separated operational health, AI supervision,
> scheduler decisions, source monitoring, historical analytics, and quality
> coverage so each metric keeps a clear meaning. This is what makes the
> supervision layer reliable and defensible.
