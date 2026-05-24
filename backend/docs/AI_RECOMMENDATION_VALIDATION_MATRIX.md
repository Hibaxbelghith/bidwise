# BidWise AI Recommendation Validation Matrix

## Objective

This matrix validates the recommendation engine before freezing the AI scope.
It is designed to test the complete product behavior, not only skill matching.

Signals covered:

- target roles;
- profile skills;
- CV semantic extraction;
- ESCO normalized skills;
- Gemini opportunity enrichment;
- contract preferences;
- work mode preferences;
- location preferences;
- experience level;
- sector/domain preferences;
- sparse/incomplete profiles;
- noisy or incorrect CV content;
- frontend explainability.

## Freeze Rule

After this validation phase:

- fix critical false positives;
- fix unclear or misleading UI explanations;
- document acceptable limitations;
- do not add a new model, new architecture, or large scoring rewrite before the
  PFE deadline.

## Validation Scale

Use this status for each scenario:

```text
PASS     top results and reasons are coherent
WARNING  acceptable limitation or minor ranking imperfection
FAIL     critical false positive, fallback leak, wrong confidence, or misleading explanation
```

## Common Checks

For each scenario, verify:

- top 5 opportunities are coherent;
- no obvious unrelated job appears in top 3;
- score and confidence feel reasonable;
- reasons explain real evidence;
- `Review before applying` shows useful gaps;
- experience, location, contract, work mode, and sector/domain signals do not
  overpower role and skill evidence alone;
- no `Recent` fallback appears in For You;
- detail page shows `Your fit` and a decision verdict;
- Gemini family signal appears only when relevant.

## Manual Test Matrix

| ID | Scenario | Profile Input | CV Input | Preferences | Expected Result | UI Checks | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R01 | Frontend complete profile | Role: `Frontend Developer`; Skills: `React`, `JavaScript`, `Node.js` | CV mentions React UI, components, responsive pages | Remote or Hybrid; Tunis; CDI | `Frontend React Developer` or similar should be top 1-3; backend-heavy JS should not be top 1 | Role, Skills, Work mode, Location chips; gaps: TypeScript/CSS acceptable | PASS | Backend validator quick run with full candidate pool: `Frontend React Developer` ranked #1. Manual UI retest still recommended before freeze. |
| R02 | Backend complete profile | Role: `Python Backend Developer`; Skills: `Python`, `Django`, `FastAPI` | CV mentions REST APIs, PostgreSQL, Redis | Hybrid; Tunis; CDI | Python/Django/FastAPI/backend offers before fullstack or AI-only jobs | Reasons mention Python/Django and role alignment | PASS | Python backend offers ranked top; fullstack and AI/network Python appear lower. |
| R03 | Fullstack profile | Role: `Full Stack Developer`; Skills: `React`, `Node.js`, `PostgreSQL` | CV mentions frontend + backend projects | Hybrid; Tunis; CDI | Fullstack and JS stack offers should rank above pure frontend/backend when evidence is balanced | Family/reasoning should not over-penalize fullstack | PASS | Full Stack Developer ranked top; frontend/backend variants appear as relevant alternatives. |
| R04 | Commercial profile | Role: `Business Development Manager`; Skills: `CRM`, `Techniques de vente`, `Prospection` | CV mentions sales pipeline, clients, negotiation | On-site; Tunisia; CDI | Business development, BDR, commercial roles rank high | `Same job family as your profile` may appear | PASS | Business Development Manager ranked top with family signal. |
| R05 | Accounting profile | Role: `Comptable`; Skills: `Comptabilite`, `Excel`, `Sage` | CV mentions invoices, accounting entries, payroll | On-site; Tunis/Sousse; CDI | Comptable/finance roles before generic Excel/operations roles | Gaps should not over-focus on unrelated tools | TODO | |
| R06 | Quality/industry profile | Role: `Quality Engineer`; Skills: `Controle qualite`, `ISO`, `Production` | CV mentions quality control and production | On-site; Tunisia; CDI | Quality engineer, production quality, ISO/industry roles rank high | Quality/industry family should support ranking | TODO | |
| R07 | Data/AI profile | Role: `Data Scientist`; Skills: `Python`, `Machine Learning`, `NLP` | CV mentions models, embeddings, PyTorch | Hybrid/Remote; Tunis; CDI | Data/AI offers rank above backend-only Python jobs | Skills and semantic/CV signals visible | TODO | |
| R08 | Marketing profile | Role: `Digital Marketing Specialist`; Skills: `Marketing digital`, `SEO`, `Content Marketing` | CV mentions campaigns, analytics, social media | Hybrid; Tunis; CDI | Marketing/content/community roles rank above sales-only roles | Family signal should distinguish marketing from pure sales | TODO | |
| R09 | HR profile | Role: `HR Manager`; Skills: `Recruitment`, `Payroll`, `HR` | CV mentions recruitment, onboarding, HR admin | On-site; Tunis; CDI | HR jobs rank high; engineering/sales false positives absent | Reasons should not rely only on location | TODO | |
| R10 | IT support/network profile | Role: `Network Engineer`; Skills: `Cisco`, `BGP`, `Routing`, `Support` | CV mentions troubleshooting and network config | On-site; Tunis; CDI | Network/support jobs rank above generic IT jobs | Skills/family signal should be visible if data exists | PASS | Backend validator quick run with full candidate pool: network/support jobs ranked top; cleaning/service support false positive guarded by automated test. Manual UI retest still recommended before freeze. |
| R11 | Junior profile vs senior jobs | Role: `Frontend Developer`; Skills: `React`, `JavaScript`; Experience: Junior/1 year | CV junior projects | Remote; CDI | Senior frontend/backend roles should be penalized or lower | Gaps mention experience if available | TODO | |
| R12 | Senior profile vs junior jobs | Role: `Backend Developer`; Skills: `Python`, `Django`; Experience: Senior/6+ years | CV senior architecture/leadership | Hybrid; CDI | Senior/lead/backend roles should rank above junior-only jobs | Confidence should reflect strong signals | TODO | |
| R13 | Remote-only preference | Any tech profile | Normal CV | Work mode: Remote only | Remote jobs should receive visible preference boost; on-site should not dominate unless very strong | `Remote work preference aligned` when relevant | TODO | |
| R14 | Contract mismatch | Role/skills strong; Employment type: Internship only | Student CV | Internship; Tunis | Full-time CDI jobs should be filtered or strongly reduced when internship-only is selected | No misleading `Good fit` for hard incompatible CDI | TODO | |
| R15 | Location preference mismatch | Role/skills strong; Location: Sfax only | Normal CV | Sfax; Remote off | Tunis jobs can appear only if evidence strong; location gap should be visible | `Location may differ` for mismatch | TODO | |
| R16 | No CV but complete profile | Role and skills filled; no active resume | Empty/no CV | Normal preferences | Ranking should still work from profile fields; confidence may be Medium | UI should not claim CV signal | TODO | |
| R17 | CV-rich but weak profile | Few skills/roles; CV contains strong backend signals | CV mentions Python/Django/FastAPI | Partial preferences | Recommendations should work but may show partial profile warning | No overconfidence from CV alone | TODO | |
| R18 | Noisy CV | Profile frontend; CV contains generic phrases: `team`, `pressure`, `creating`, `manage` | No real skills or polluted CV | Normal preferences | CV noise should not create unrelated recommendations | No strange skill reasons from noise | TODO | |
| R19 | Incorrect CV domain | Profile accounting; CV text is unrelated marketing or frontend | Contradictory CV | Accounting preferences | Profile intent should dominate; unrelated CV should not hijack ranking | Reasons should focus on profile, not wrong CV | TODO | |
| R20 | Very incomplete profile | No skills, no roles, no CV; only location | Empty | Location only | For You should show empty/insufficient state, not fake recommendations | No fallback `Recent` visible | TODO | |
| R21 | Offer with no skills but Gemini family | Commercial profile; opportunity enriched as `sales` | Normal sales CV | Normal preferences | Gemini-enriched sales opportunity can rank with family evidence | `Same job family as your profile` visible | TODO | |
| R22 | Offer with generic skills only | Quality or sales profile; offer skills: `Gestion`, `Qualite`, `Production` | Normal CV | Normal preferences | Generic skills should not overpower role/family/semantic evidence | Reasons should avoid vague one-word noise | TODO | |
| R23 | Backend-heavy fullstack vs frontend | Frontend profile | React CV | Remote; CDI | True frontend jobs should rank above backend-heavy JS/fullstack jobs | Top 1 should be frontend if available | TODO | |
| R24 | Python backend vs AI Python | Backend profile | Django/FastAPI CV | Hybrid; CDI | Backend API jobs should rank above AI Engineer when role is backend | AI Engineer may appear lower as worth reviewing | TODO | |
| R25 | Arabic/multilingual opportunity | Backend profile | FR/EN CV | Hybrid; CDI | Arabic/Python/Django opportunity can appear if skill evidence exists | Language should not break matching completely | TODO | |
| R26 | Experience hard mismatch - junior profile | Role: `Frontend Developer`; Skills: `React`, `JavaScript`; Experience: Junior/0-1 year | Junior projects, no leadership | Remote/Hybrid; Tunis; CDI | Junior/frontend roles should rank above senior/lead/fullstack jobs even if semantic score is close | `Review before applying` should mention experience gap when senior job appears | WARNING | Junior frontend ranked first and senior fullstack was demoted with an experience gap, but a generic senior IT/ERP JavaScript job still appeared high. Needs frontend/role-specific retest after R01 cleanup. |
| R27 | Experience senior intent | Role: `Backend Lead` or `Senior Backend Developer`; Skills: `Python`, `Django`, `Architecture`; Experience: Senior/6+ years | CV mentions architecture, mentoring, production systems | Hybrid; Tunis; CDI | Senior/lead/backend roles should rank above junior backend jobs | Confidence should not be high for junior-only jobs | TODO | |
| R28 | Location strong preference - non-remote | Role: `Comptable`; Skills: `Comptabilite`, `Excel`; Location: `Sousse`; Remote off | Accounting CV | On-site; Sousse; CDI | Sousse accounting jobs should rank above similar Tunis jobs unless Tunis job has much stronger metier evidence | Location chip/gap must be visible | PASS | Backend validator quick run: accounting jobs ranked top with Sousse accounting offers visible in top 5. Location supports ranking without replacing metier evidence. |
| R29 | Location flexible with remote | Role: `Frontend Developer`; Skills: `React`, `JavaScript`; Location: `Tunis`; Remote enabled | React CV | Remote; CDI | Remote jobs outside Tunis can rank well; on-site distant jobs should be lower | `Remote work preference aligned` should appear only for remote/hybrid opportunities | TODO | |
| R30 | Sector/domain preference alignment | Role: `Backend Developer`; Skills: `Python`, `Django`; Domain: `Fintech` or `Banking` | Backend CV with payment/API projects | Hybrid; Tunis; CDI | Backend fintech/banking offers should get a small boost, but unrelated fintech sales jobs should not outrank backend jobs | Sector signal should support, not dominate | PASS | Backend validator quick run with full candidate pool: Python/backend jobs ranked top and unrelated sector jobs did not dominate. Sector remains a lightweight support signal. |
| R31 | Sector/domain mismatch | Role: `Marketing Specialist`; Skills: `SEO`, `Content Marketing`; Domain: `Marketing digital` | Marketing CV | Hybrid; Tunis; CDI | HR/accounting/IT jobs in same location should not rank high only due location/contract | Reasons should not rely only on preferences | WARNING | SEO marketing offer ranked first and reasons used skill/location/industry, not preferences only. Sector input was unreliable because autocomplete forced `Fintech` for `finance`; fixed, retest needed. |

## Backend API Validation

For selected scenarios, inspect:

```http
GET /api/recommendations/?limit=20
```

Fields to verify:

```json
{
  "score": 0.75,
  "recommendation_confidence": "HIGH",
  "reasons": [],
  "gaps": [],
  "evidence_summary": {
    "skill_overlap": 2,
    "profile_skill_overlap": 2,
    "role_match": true,
    "llm_family_match": true,
    "llm_family_mismatch": false,
    "matched_llm_families": ["frontend"]
  }
}
```

## Technical Validation Commands

Run before freezing:

```bash
docker compose exec backend python manage.py check
docker compose run --rm backend python manage.py test tests.test_recommendation_quality_gates tests.test_recommendation_normalized_skill_bonus tests.test_llm_enrichment tests.test_llm_opportunity_enrichment --keepdb
npm --prefix frontend run build
```

Optional Gemini enrichment smoke test, respecting quota:

```bash
docker compose exec backend python manage.py enrich_opportunities_with_gemini --limit 2 --delay-seconds 20
```

## Decision Log

Fill after manual validation:

```text
Recommendation freeze decision:

Critical failures found:

Warnings accepted:

Fixes applied:

Remaining limitations for soutenance:

Post-PFE improvements:
```
