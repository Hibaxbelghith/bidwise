# Organization Dashboard

This document explains the BidWise organization workspace used by promoters to
publish opportunities directly on the platform.

## Purpose

Organizations can create a dedicated organization account, complete their
organization profile, and publish opportunities from the organization dashboard.
The supported opportunity types are:

- Job (`EMPLOI`)
- Internship (`STAGE`)
- Seasonal job (`SAISONNIER`)
- Call for tender (`PROJET`)

The organization dashboard lists only the opportunities published by the
connected organization account.

## API Endpoints

### List organization opportunities

`GET /api/organization/opportunities/`

Access rules:

- Authenticated organization account: allowed
- Authenticated candidate account: `403`
- Anonymous user: `401`
- Organization account without organization profile: `403`

The response contains only opportunities where `organisation` is the connected
organization user.

### Create organization opportunity

`POST /api/organization/opportunities/`

Access rules are the same as the list endpoint.

The backend validates all business fields server-side:

- Tunisian location whitelist
- required fields by opportunity type
- non-negative experience and salary values
- date constraints
- internship-specific details
- seasonal-specific details
- call-for-tender-specific details, lots, and documents

Created opportunities are currently stored with source `BidWise Organizations`
and linked to the publishing organization account.

### Upload tender document

`POST /api/organization/opportunities/tender-documents/`

This endpoint accepts multipart uploads for call-for-tender documents.

Accepted files:

- PDF
- DOCX
- DOC

Maximum size: `5 MB`

The backend stores the file through the same storage abstraction used for
profile resumes. When Cloudinary is enabled, uploaded tender documents are
stored externally and the API returns a public URL. The call-for-tender form then
sends that URL inside `project_details.documents`.

## Anti-Abuse Protection

### Publication rate limit

The `POST /api/organization/opportunities/` endpoint is rate limited per
authenticated organization user.

Default rate:

```text
5 publications / hour / organization
```

Configuration:

```env
ORGANIZATION_OPPORTUNITY_POST_RATE=5/hour
```

The rate limit applies only to `POST` requests. `GET` requests are not throttled
so the organization can continue viewing its dashboard even after reaching the
publish quota.

When the quota is exceeded, the API returns:

```text
429 Too Many Requests
```

### Why rate limiting matters

Rate limiting protects the platform against:

- automated spam scripts
- accidental repeated submissions
- mass posting by a compromised organization account
- unnecessary load on future moderation or AI validation systems

It is a volume protection layer. It does not replace content moderation,
CAPTCHA, or backend validation.

### Turnstile CAPTCHA

Organization publishing can be protected with Cloudflare Turnstile.

Backend configuration:

```env
TURNSTILE_SECRET_KEY=your-cloudflare-turnstile-secret
TURNSTILE_TIMEOUT_SECONDS=4.0
```

Frontend configuration:

```env
VITE_TURNSTILE_SITE_KEY=your-cloudflare-turnstile-site-key
```

Behavior:

- If `TURNSTILE_SECRET_KEY` is empty, backend verification is disabled. This is
  useful for local development and automated tests.
- If `TURNSTILE_SECRET_KEY` is configured, `POST /api/organization/opportunities/`
  requires a valid `turnstile_token`.
- The frontend displays the Turnstile widget only when
  `VITE_TURNSTILE_SITE_KEY` is configured.
- Invalid or missing tokens return `400 Bad Request` with a
  `turnstile_token` field error.

Turnstile is an anti-bot layer. It does not decide whether the opportunity
content is legitimate.

## Moderation Flow

BidWise separates form validation from semantic moderation:

1. The serializer validates structure and form rules.
2. Turnstile and rate limiting protect the endpoint against automated abuse.
3. A Gemini-based moderation classifier reviews a compact opportunity payload.
4. The final status is stored as `ACTIVE` only when the LLM decision is
   `approved`; all other decisions remain `PENDING_REVIEW` for admin control.

The moderation classifier receives only business-relevant content:

- opportunity type, title, description
- contract, salary, experience, skills
- type-specific details for internships, seasonal jobs, and tenders

It does not receive internal IDs, technical timestamps, organization reputation
signals, or tender document URLs. This avoids penalizing new organizations and
keeps the judgment focused on whether the content is a real professional
opportunity.

The moderation audit is stored in `extra_data["moderation"]`:

```json
{
  "llm": {
    "skipped": false,
    "provider": "gemini",
    "model": "gemini-1.5-flash",
    "category": "scam",
    "decision": "rejected",
    "confidence": 1.0,
    "reason": "The candidate is asked to pay fees before starting.",
    "final_decision": "rejected"
  },
  "final_decision": "rejected",
  "final_status": "PENDING_REVIEW"
}
```

The prompt uses a strict moderation taxonomy:

- `legitimate_opportunity`
- `scam`
- `mlm_or_pyramid`
- `advertisement`
- `inappropriate_content`
- `irrelevant`
- `unclear`

The classifier is instructed to approve clear professional opportunities and to
reject only when a specific hard signal is present, such as a request for the
candidate to pay money. Public tender financial fields such as
`cautionnement provisoire`, budgets, and buyer-side amounts are explicitly
treated as normal procurement information, not scams.

The `reason` field is requested in English so the admin dashboard remains
consistent even when submitted opportunities are written in French, Arabic,
English, or mixed language.
