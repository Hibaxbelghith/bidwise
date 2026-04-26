# BidWise - Project status

Last updated: 2026-04-26

## Executive summary

- Sprint 1: complete
- Sprint 2: complete
- Sprint 3: next

## Sprint 1

Delivered:
- passwordless OTP authentication,
- Google Sign-In,
- JWT rotation and blacklist,
- onboarding flows,
- suspicious login protection,
- web and mobile auth UX foundations.

## Sprint 2

Status: technically complete for the opportunities pipeline scope.

Delivered:
- end-to-end pipeline from collection to API,
- raw snapshot persistence through `RawOpportunite`,
- deterministic normalization and enrichment,
- quality scoring and gating,
- non-destructive materialization into `Opportunite`,
- dataset and pipeline metrics commands,
- embedding generation and similarity endpoints,
- client-facing browse/detail APIs used by web and mobile apps.

Validated Sprint 2 source scope:
- Keejob
- EmploiTunisie

Additional connectors already present in the codebase:
- LinkedIn
- MarchesPublics

## Non-blocking backlog

- hard duplicate cleanup in the dataset,
- release smoke run in a live Docker environment before final push,
- Sprint 3 personalization and user action flows.

## Source of truth

- `backend/docs/SPRINT2_RECAP.md`
- `backend/docs/SPRINT2_TESTING_GUIDE.md`
- `README.md`
