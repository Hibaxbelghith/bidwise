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

### Update an organization opportunity

`PATCH /api/organization/opportunities/{id}/`

The connected organization can partially update only its own opportunities.
The backend reconstructs the complete opportunity, merges the submitted fields,
and runs the same server-side validation used during creation. This prevents a
partial request from bypassing cross-field or type-specific rules.

Editable fields:

- title, description, and Tunisian location
- contract, availability, experience, education, salary, and skills
- deadline
- internship, seasonal, or call-for-tender details matching the existing type

Protected fields such as the opportunity type, status, organization, source,
publication metadata, moderation data, and application count cannot be changed.
Unknown fields are also rejected.

Status behavior:

- `ACTIVE` and `PENDING_REVIEW` opportunities can be corrected and re-moderated.
- `REJECTED` opportunities can be corrected, but always return to
  `PENDING_REVIEW`, even when the LLM classifies the corrected content as
  approved. A previous rejection must be reviewed by an administrator.
- `SUSPENDUE` opportunities can be corrected and re-moderated while remaining
  suspended. The moderation result determines whether a later activation
  returns to `ACTIVE` or `PENDING_REVIEW`.
- `FERMEE`, `ARCHIVEE`, and `EXPIREE` opportunities return `409 Conflict`.
- The complete updated content is sent through LLM moderation again.
- For an ordinary editable opportunity, an explicitly approved result returns
  it to `ACTIVE`; every other result, including provider failure, keeps it in
  `PENDING_REVIEW`.
- The previous moderation result is retained in a bounded history and the
  changed fields are recorded in the immutable audit log.

An organization cannot discover or modify another organization's opportunity:
the endpoint returns `404 Not Found`.

The organization dashboard routes the `Edit` action to the form matching the
stored opportunity type. The form is prefilled from the organization API and
uses the same field validation and error summary as publication. Turnstile is
loaded before submission and displays its current state; the save button remains
disabled until verification succeeds. The dashboard hides the `Edit` action for
`FERMEE`, `ARCHIVEE`, and `EXPIREE` opportunities.

### Organization status actions

Organization opportunities support explicit business statuses without deleting
the database row:

- `SUSPENDUE`: temporarily hidden and reversible.
- `FERMEE`: closed and hidden, but reversible from the organization dashboard.

Endpoints:

```text
POST /api/organization/opportunities/{id}/suspend/
POST /api/organization/opportunities/{id}/activate/
POST /api/organization/opportunities/{id}/close/
```

Allowed transitions:

```text
ACTIVE         -> SUSPENDUE | FERMEE
PENDING_REVIEW -> SUSPENDUE | FERMEE
SUSPENDUE      -> ACTIVE or PENDING_REVIEW | FERMEE
FERMEE         -> ACTIVE or PENDING_REVIEW | SUSPENDUE
REJECTED       -> FERMEE
```

The status menu exposes only the organization actions `Active`, `Suspended`, and
`Closed`. `Pending` is a moderation result, not an organization action. When an
opportunity originated from `PENDING_REVIEW`, selecting `Active` keeps or returns
it to `PENDING_REVIEW`; this prevents status changes from bypassing moderation.
The original moderation state is preserved across chains such as
`PENDING_REVIEW -> SUSPENDUE -> FERMEE -> activate`.

Closing an already closed opportunity is idempotent. `ARCHIVEE` and `EXPIREE`
cannot be changed by an organization. Suspended and closed opportunities remain
visible in organization/admin dashboards and audit logs, but are removed from
public listing, direct candidate access, recommendations, and new applications.

### Deadline lifecycle

Deadline validation and opportunity expiration are separate concerns:

- Calls for tender require `date_limite` and a deadline time.
- Jobs may have an optional application deadline.
- Internships primarily store a start date and duration in
  `internship_details`.
- Seasonal jobs store their execution period in `seasonal_details`, including
  an end date.
- Scraped sources do not all expose a structured deadline.

The normalization pipeline can set `EXPIREE` while processing a record whose
deadline is already in the past. Some source adapters also preserve an explicit
expired status reported by the source website.

Celery Beat runs `opportunities.expire_organization_opportunities` hourly at
minute `05`. The task is intentionally limited to organization-published
opportunities currently in `ACTIVE` status:

- `date_limite < current local date` becomes `EXPIREE`;
- seasonal `end_date < current local date` becomes `EXPIREE`;
- a date equal to the current local date remains active until the next day;
- opportunities without either reliable date remain unchanged.

`PENDING_REVIEW`, `REJECTED`, `SUSPENDUE`, `FERMEE`, `ARCHIVEE`, and already
`EXPIREE` opportunities are preserved. Scraped opportunities remain managed by
their source synchronization and are not touched by this task.

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
## Admin Decision Email Notifications

When an administrator approves or rejects an organization opportunity after
manual review, BidWise sends an asynchronous email to the organization account.

Flow:

1. The status, moderation decision, and audit log are committed in one database
   transaction.
2. `transaction.on_commit()` dispatches
   `opportunities.send_organization_admin_decision_email`.
3. Celery sends the email through the configured Django email backend.
4. When `SENDGRID_API_KEY` is configured, the SendGrid Web API backend is used.

Notifications are sent only for a real decision:

- Admin approval sends a link to the public opportunity.
- Admin rejection sends the public admin note, or a generic message when no
  note was provided.
- Repeated decisions do not send duplicate emails.
- `PENDING_REVIEW` does not trigger an email.

The task verifies the decision timestamp before delivery and stores delivery
state in `extra_data["moderation"]["admin_decision"]["email_notification"]`.
Raw LLM explanations, confidence, provider, and internal metadata are never
included in organization emails.

Configuration:

```env
SENDGRID_API_KEY=your-sendgrid-api-key
DEFAULT_FROM_EMAIL=BidWise <verified-sender@example.com>
BIDWISE_FRONTEND_URL=http://localhost:5173
BIDWISE_SUPPORT_EMAIL=support@example.com
```
