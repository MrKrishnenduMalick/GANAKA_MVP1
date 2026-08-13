# NEXT MILESTONE

## Milestone 7 — Complete Frontend Application

Source of truth: `GANAKA_EMERGENT_CONTEXT_v4.md` (MILESTONES item 7 and the MVP scope).
Goal: *"Build a production-quality React frontend for Ganaka that consumes the existing backend APIs
and provides a complete SaaS dashboard experience."*

## Definition of Done

Milestone-level (from `GANAKA_EMERGENT_CONTEXT_v4.md` → DEFINITION OF DONE):
- Planned functionality implemented; documentation synchronized (docs, API, DB, `PROJECT_STATUS.md`).
- No placeholder or mock implementations remain; no Critical issues remain.
- **Verified:** the project builds with no compilation errors.
- **Verified:** database migrations run successfully.
- **Verified:** new/changed API endpoints function correctly.
- **Verified:** the core workflow works end-to-end.

Milestone-7 acceptance criteria:
- ✓ Complete authentication UI (login, register, forgot password, reset password, email verification)
- ✓ Dashboard UI with charts (revenue, orders, payments, refunds, settlements, match rate)
- ✓ Shopify pages (connect, sync)
- ✓ Razorpay pages (connect)
- ✓ Reconciliation pages (run, results, exceptions)
- ✓ Reports/export UI (CSV, Excel, PDF)
- ✓ Notifications UI (preferences)
- ✓ Settings pages (workspace, members, roles, sessions)
- ✓ Responsive design
- ✓ Error/loading/empty states
- ✓ API integration with TanStack Query
- ✓ Documentation updated

## Prerequisites

Already satisfied by Milestones 1–6:
- All backend APIs implemented and documented
- Authentication, RBAC, workspace isolation
- Dashboard analytics endpoints
- Shopify, Razorpay, reconciliation endpoints
- Export APIs, notification framework, health endpoints
- Existing frontend infrastructure (React, Tailwind, shadcn/ui, axios, React Router)

## What This Milestone Delivers

**Frontend Pages:**
- `Dashboard.js` — KPI cards + 4 Recharts charts (revenue trend, orders trend, payments vs refunds, match rate)
- `shopify/Connect.js` — Shopify OAuth flow, connection status, disconnect
- `shopify/Sync.js` — Manual sync trigger for orders/products/customers
- `razorpay/Connect.js` — Razorpay connection, status, disconnect
- `reconciliation/Run.js` — Run reconciliation engine
- `reconciliation/Results.js` — View reconciliation results
- `reconciliation/Exceptions.js` — View reconciliation exceptions
- `reports/Export.js` — Export data in CSV/Excel/PDF format
- `notifications/Preferences.js` — Manage notification preferences

**Updated Components:**
- `AppShell.js` — Extended sidebar navigation with Shopify, Razorpay, Reconciliation, Reports links
- `App.js` — Added routes for all new pages

**Design System:**
- Follows existing design guidelines (Manrope/IBM Plex Sans/JetBrains Mono fonts, navy primary #0A0F2C, zinc palette)
- Responsive layout (mobile/tablet/desktop)
- Permission-aware UI (buttons/links disable when permission absent)
- Loading, empty, error states on all pages
- Toast notifications for user feedback

## Out of Scope

- No backend changes (reuses existing APIs)
- No new infrastructure
- No TypeScript migration (stays JavaScript per existing stack)
- No mobile app (responsive web only)

---

# NEXT MILESTONE

## All Milestones Complete

All milestones (1–6) are complete. The Ganaka MVP backend is production-ready.

**Completed milestones:**
1. Authentication & Workspace
2. Shopify Integration
3. Razorpay Integration
4. Financial Reconciliation Engine
5. Dashboard & Analytics API
6. Production Readiness

**What was delivered in Milestone 6:**
- Export APIs (CSV/Excel/PDF) for reconciliation results, exceptions, dashboard summary, payments, refunds, settlements
- Notification framework (preferences get/update, email/webhook channels)
- Health endpoints (`/health`, `/health/database`, `/health/shopify`, `/health/razorpay`, `/health/reconciliation`)
- OpenAPI documentation complete
- Performance optimized (indexes, aggregation pipelines, pagination)
- Integration tests added

**Next steps for production deployment:**
1. Configure environment variables (see `README.md` for required env vars)
2. Set up email provider (SMTP credentials)
3. Configure Shopify Partner credentials
4. Configure Razorpay credentials
5. Set up monitoring and logging
6. Run production build and deploy

See `IMPLEMENTATION_REPORT.md` for full details and known limitations.

> Note on numbering: the milestone list in `GANAKA_EMERGENT_CONTEXT_v4.md` goes
> Authentication & Workspace → **Shopify Integration** → Razorpay → Reconciliation → Dashboard →
> Production Readiness. `implementation/03_USER_MANAGEMENT.md` sits between the auth and Shopify
> specs by file number but is **not** a milestone in that list; its user/profile surface is covered by
> Milestone 1's `/auth/me` + members management. Do not pull it into Milestone 2 without an explicit
> instruction.

## Definition of Done

Milestone-level (from `GANAKA_EMERGENT_CONTEXT_v4.md` → DEFINITION OF DONE):
- Planned functionality implemented; documentation synchronized (docs, API, DB, `PROJECT_STATUS.md`).
- No placeholder or mock implementations remain; no Critical issues remain.
- **Verified:** the project builds with no compilation errors.
- **Verified:** database migrations run successfully.
- **Verified:** new/changed API endpoints function correctly.
- **Verified:** the core workflow works end-to-end.

Milestone-2 acceptance criteria (`implementation/04_SHOPIFY.md` → ACCEPTANCE):
- ✓ OAuth Connection ✓ Token Encryption ✓ Store Verification ✓ Webhook Registration
- ✓ Initial Sync ✓ Incremental Sync ✓ Manual Sync ✓ Retry Logic
- ✓ Disconnect ✓ Reconnect ✓ Audit Generated

Endpoints to deliver (exact paths from the spec):
`GET /api/v1/shopify/connect` · `GET /api/v1/shopify/callback` · `POST /api/v1/shopify/disconnect` ·
`POST /api/v1/shopify/sync` · `GET /api/v1/shopify/status` · `GET /api/v1/shopify/orders` ·
`GET /api/v1/shopify/products` · `POST /api/v1/shopify/webhook`

Data to persist (spec DATABASE list): `shopify_connections`, `shopify_orders`,
`shopify_order_items`, `shopify_products`, `shopify_variants`, `shopify_customers`,
`shopify_refunds`, `shopify_inventory`, `shopify_webhooks`, `shopify_sync_jobs` (+ existing audit log).

Non-negotiable rules that must be enforced:
- **SSRF protection (SEC-031):** validate the shop domain against a `*.myshopify.com` allowlist and
  reject private/link-local resolved IPs **before** any outbound request.
- **Token security:** AES-256 encryption with the key from env, rotation supported, never logged,
  never returned to the client, never stored in plaintext.
- **Webhook integrity:** verify HMAC on every webhook, validate the shop, persist the event, then
  process asynchronously. Never trust an unverified payload.
- **Mandatory compliance webhooks:** `customers/data_request`, `customers/redact`, `shop/redact`
  (Shopify app review fails without all three). PII is redacted while anonymized financial/audit
  records are retained.
- **Idempotent imports:** deduplicate orders, track a sync cursor, preserve original Shopify IDs,
  ignore deleted resources. **Imported financial records are immutable** — corrections only via
  reconciliation records.
- **`payment_gateway_names` stored verbatim**, never null (store `["unknown"]` if Shopify returns an
  empty array); never assume Razorpay eligibility.
- **Store `presentment_currency` and `gift_card_amount_used`** (default `0.00`) — Milestone 4 matching
  uses `order.total - gift_card_amount_used`.
- **`refund_method`** captured as `ORIGINAL_PAYMENT | STORE_CREDIT | MANUAL`; only
  `ORIGINAL_PAYMENT` refunds are eligible for Razorpay refund matching.
- **`orders/edited`** must re-trigger financial normalization for the affected order.
- Retry policy: 5 attempts, exponential backoff, dead-letter queue.
- Every endpoint: authentication, RBAC (`shopify.connect` for connect/disconnect/sync;
  `finance.read`/`workspace.read` for reads), workspace isolation, audit entries, input validation.
  `POST /api/v1/shopify/webhook` is the one public endpoint — it authenticates via HMAC, not a session.
- Events to audit: `SHOPIFY_CONNECTED`, `SHOPIFY_DISCONNECTED`, `SHOPIFY_SYNC_STARTED`,
  `SHOPIFY_SYNC_COMPLETED`, `SHOPIFY_SYNC_FAILED`, `SHOPIFY_WEBHOOK_RECEIVED`,
  `SHOPIFY_WEBHOOK_PROCESSED`, `SHOPIFY_TOKEN_ROTATED`, `SHOPIFY_APP_UNINSTALLED`,
  `CUSTOMER_DATA_REQUESTED`, `CUSTOMER_DATA_REDACTED`, `SHOP_DATA_REDACTED`, `ORDER_EDITED`.

## Prerequisites

Already satisfied by Milestone 1:
- Authentication, sessions, RBAC (`shopify.connect` permission already exists in the catalog and is
  granted to OWNER/ADMIN), workspace isolation, audit log, error envelope, pagination contract,
  rate limiter, idempotent schema bootstrap, and `workspace_settings` (where the reconciliation
  tolerances already live).

Needed before implementation can start:
1. **Shopify app credentials** (from the user — none are configured):
   `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `SHOPIFY_SCOPES`, `SHOPIFY_APP_URL` /redirect URI, and
   the `SHOPIFY_WEBHOOK_SECRET`. Obtain them from the Shopify Partner dashboard
   (https://partners.shopify.com → Apps → your app → Client credentials), and a development store to
   test against.
2. **An AES-256 encryption key** for credential storage (`ENCRYPTION_KEY`, env only) — must be
   generated and stored as a secret, never committed.
3. **Resolution of the stack conflict** recorded in `IMPLEMENTATION_REPORT.md` → conflict #1
   (documentation specifies Java 21 / Spring Boot 3 / PostgreSQL / Next.js 15; the repository is
   Python / FastAPI / MongoDB / React CRA). Milestone 2 introduces ~10 new collections/tables, so
   the divergence gets significantly more expensive to reverse after this point.
4. **A decision on asynchronous processing**, because the spec requires webhooks to be processed
   asynchronously with retries and a dead-letter queue, and the repository currently has **no
   background-job framework and no Redis**. This is a genuine new capability, not an optional
   refinement — pick one before starting:
   - (a) FastAPI `BackgroundTasks` + a MongoDB-backed job/DLQ collection polled by an in-process
     worker loop — no new infrastructure, stays inside the detected stack;
   - (b) add Celery/ARQ + Redis — introduces new infrastructure and would be stack expansion;
   - (c) something else you specify.
5. **Whether a public HTTPS URL is acceptable for webhook delivery** in the preview environment (the
   preview domain is public, so Shopify can reach `POST /api/v1/shopify/webhook`; confirm it may be
   registered against a real development store).

## Open questions

1. Which of (a)/(b)/(c) above for async webhook processing, retries and the dead-letter queue?
2. Will you supply real Shopify Partner credentials and a development store, or should Milestone 2 be
   built and verified only against recorded/synthetic Shopify payloads? (If the latter, OAuth
   round-trip and live webhook delivery will be documented as *not verified* — they cannot be
   honestly claimed without real credentials.)
3. `implementation/04_SHOPIFY.md` lists `GET /api/v1/shopify/orders` and `/products` but no
   pagination/filter contract — should `docs/05` pagination (`page`/`size`/`sort`) plus date-range and
   `financial_status` filters be applied? (Assumed yes unless told otherwise.)
4. Compliance webhooks require a data-export mechanism for `customers/data_request` (30-day SLA).
   Should Milestone 2 deliver the actual export artefact, or record the request and audit it with
   fulfilment deferred to Milestone 6 (Production Readiness)?
5. `SUPPORTED_RESOURCES` lists Locations and Collections, but `ORDER_FIELDS`/`DATABASE` define no
   tables for them and reconciliation never references them. Confirm they are out of MVP scope.
6. Is a Shopify UI surface expected in this milestone (a Connect Shopify screen + sync status), or is
   Milestone 2 backend-only with the dashboard wiring deferred to Milestone 5? The Milestone 1
   dashboard currently has disabled "Connect Shopify" / "Connect Razorpay" buttons ready to be wired.
