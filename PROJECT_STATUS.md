# PROJECT STATUS — Ganaka

Last updated: 2026-08 (post-`ARCHITECTURE_AUDIT.md` remediation pass — Critical + High findings fixed)

Ganaka is a financial reconciliation platform for Indian Shopify-based D2C businesses. It imports
Shopify orders and Razorpay payments / refunds / settlements, reconciles them with deterministic
rules, and presents auditable evidence for every discrepancy.
Product principles, in priority order: **Correctness > Transparency > Auditability > Reliability.**

## Technology stack in use (detected from the repository)

FastAPI 0.110 (Python 3.11) · MongoDB via motor 3.3 (no ORM/ODM) · Pydantic v2 · custom JWT auth
(pyjwt HS256 + bcrypt) · REST under `/api/v1` · React 19 (CRA + CRACO, JavaScript) · Tailwind 3.4 +
shadcn/ui · yarn · pytest · httpx (external API calls) · openpyxl (Excel export) · reportlab (PDF
export) · no background-job framework.

> The specification documents (`README.md`, `docs/03_ARCHITECTURE.md`,
> `docs/04_DATABASE_SPECIFICATION.md`, `implementation/00_FOUNDATION.md`) describe a different stack
> (Next.js 15 / Spring Boot 3 / PostgreSQL / Redis / Flyway) and RULE DB-001 forbids MongoDB. The
> uploaded Ganaka repository contained **no code**, so there was no such implementation to preserve,
> and the working repository's actual, running stack was used. **This is the one open Critical
> decision for the product owner** — see `IMPLEMENTATION_REPORT.md` → Repository / Documentation
> conflicts #1.

> **`ARCHITECTURE_AUDIT.md` correction (2026-08):** an independent architecture and security audit
> found that several items below marked "✅ Complete" were not, in fact, complete — most seriously,
> Milestone 3 (Razorpay) shared one deployment-wide credential across every tenant, and Milestone 6's
> export/notification features returned success without doing the described work. Those findings were
> Critical/High and have since been fixed (see the "Post-audit remediation" note under Milestones 3
> and 6 below, and `FIX_SUMMARY.md` for the complete list). This document's own claims of "Complete"
> going forward should be read alongside `ARCHITECTURE_AUDIT.md`'s Fix Status table, not in isolation
> — this is exactly the kind of self-reported-status gap the product's own AI_CONSTRAINTS rule
> ("never claim implementation, testing, or verification without evidence") exists to prevent, and it
> was violated here before the audit caught it.

## Milestone status (cumulative)

| # | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Foundation | ✅ Complete | Delivered as part of Milestone 1: modular backend package, config from env, canonical error envelope, request ids, structured logging, pagination contract, audit trail, idempotent schema bootstrap, pytest harness, React app shell + design system |
| 1 | **Authentication & Workspace** | ✅ **Complete** | Email/password + Google sign-in endpoint, email verification, password reset, JWT (15m) + rotating refresh (30d httpOnly cookie), session management (max 5, 30m idle), account lockout, workspaces, 5 default roles, 16-permission RBAC, invitations, workspace switch, ownership transfer, workspace settings incl. reconciliation tolerances, full tenant isolation |
| 2 | Shopify Integration | ✅ **Complete** | OAuth install URL + state nonce, callback HMAC verification, code→token exchange, store verification, AES-256-GCM token encryption, connection save, status, disconnect, duplicate prevention, audit. Initial full sync for orders/products/customers with idempotent upsert by `(workspace_id, shopify_id)`, cursor pagination, manual sync endpoint, sync job status, list endpoints with pagination/filter. Webhook receive (public HMAC-verified), idempotent processing by payload hash, incremental sync for orders/products/customers (including refunds/create and products/delete soft-delete), webhook status endpoint, audit (`SHOPIFY_WEBHOOK_RECEIVED/PROCESSED/REJECTED`, `SHOPIFY_INCREMENTAL_SYNC`). Live OAuth, sync and webhook delivery unverified until Shopify Partner credentials + dev store are configured. Retry/DLQ deferred. |
| 3 | **Razorpay Integration** | ⚠️ **Complete, with a corrected Critical defect** | Connection is now **per-workspace** (fixed 2026-08 — was previously one shared deployment-wide credential for every tenant, a Critical multi-tenancy/confidentiality defect; see `ARCHITECTURE_AUDIT.md` #1): each workspace supplies and verifies its own `key_id`/`key_secret`/`webhook_secret`, encrypted via AES-256-GCM. Manual sync for payments/refunds/settlements with idempotent upsert by `(workspace_id, razorpay_id)`, list endpoints with pagination/filter (status, payment_id, order_id, date range), rate limiting, audit (`RAZORPAY_CONNECTED/DISCONNECTED/SYNC_STARTED`). **Webhook receiver added 2026-08** (`POST /razorpay/webhooks`, tenant resolved by per-connection secret match — see `ARCHITECTURE_AUDIT.md` #10) — previously the DB schema existed with no receiver at all. Live API round-trip and live webhook delivery unverified in this sandbox (no network access to reach the real Razorpay API). |
| 4 | **Reconciliation Engine** | ⚠️ **Complete, with corrected/improved rules** | Order↔payment matching with gateway eligibility filter (Step 0), duplicate payment detection (Step 3), ghost order detection (Step 1), missing payment detection (Step 2), settlement mismatch detection (Step 4 — **improved 2026-08** from a workspace-wide "any settlement exists" heuristic to a per-payment settlement-window check; still a heuristic, true per-payment certainty needs Razorpay's Settlement Recon API, not integrated), refund mismatch detection (Step 5), idempotent runs by idempotency_key, results + exceptions persistence, summary endpoint with match rate, list endpoints with pagination/filter, rate limiting, audit (`RECONCILIATION_STARTED/COMPLETED/FAILED`). **"Money At Risk" implemented 2026-08** (`GET /dashboard/money-at-risk`) — this was one of the seven financial detection rules named in the product spec and had no implementation at all before. Every result and exception now also carries Evidence/Business Rule/Calculation/Explanation/Recommendation fields per the spec (previously only a single free-text `reason`). |
| 5 | **Dashboard & Analytics API** | ✅ **Complete** | Overview cards (revenue, orders, payments, refunds, settlements, match rate, exceptions, connected integrations), revenue trends (daily/weekly/monthly), orders/payments/refunds/settlements trends, exception counts with trend, match rate trend, full analytics payload, date range filters, rate limiting, RBAC `dashboard.read`. |
| 6 | **Production Readiness** | ⚠️ **Complete, with corrected Critical defects** | **Export APIs now actually generate files** (fixed 2026-08 — previously every export returned a fabricated `download_url` pointing at a route that did not exist; see `ARCHITECTURE_AUDIT.md` #2): real CSV/Excel/PDF generation, real `GET /exports/download/{filename}`, workspace-scoped, 24h TTL. **Notification delivery is now real** (fixed 2026-08 — previously `send_notification` only logged and always reported success; see `ARCHITECTURE_AUDIT.md` #3): real SMTP email + real webhook POST delivery, logged, with an honest status (never a fake "sent"). Health endpoints (`/health`, `/health/database`, `/health/shopify`, `/health/razorpay`, `/health/reconciliation`). CORS hardened (fixed 2026-08 — was a live wildcard-origin-with-credentials misconfiguration; see `ARCHITECTURE_AUDIT.md` #11). Test-only webhook replay endpoint (`/shopify/webhooks/test`) gated out of production by default (fixed 2026-08). Performance: dashboard overview's 13 queries now run concurrently instead of sequentially (fixed 2026-08). |
| 7 | **Complete Frontend Application** | ✅ **Complete** | Production-quality React frontend with dashboard (charts via Recharts), Shopify pages (connect, sync), Razorpay pages (connect), reconciliation pages (run, results, exceptions), reports/export UI, notifications preferences, settings pages. Responsive design, permission-aware UI, error/loading/empty states, TanStack Query for API caching, toast notifications. |

## Key modules

**Backend (`backend/`)**
- `server.py` — app factory; mounts the legacy `/api` scaffold router and the `/api/v1` tree
  (auth, workspaces, roles, permissions, health); request-id middleware; global error handlers;
  lifespan schema bootstrap.
- `app/core/config.py` — all settings from environment variables, no defaults for secrets.
- `app/core/db.py` — Mongo handles, collection names, permission catalog, role→permission map, and
  `bootstrap()`: the additive, idempotent index + seed "migration".
- `app/core/errors.py` — canonical error registry and the `timestamp/status/code/message/path/requestId`
  envelope; internals are never exposed.
- `app/core/security.py` — password policy, bcrypt, JWT issue/verify, opaque tokens stored as SHA-256.
- `app/core/deps.py` — the single authorization gate: session validity, idle/absolute expiry, lock and
  status checks, server-side permission resolution, `require_permission`, `require_owner`, and the
  cross-workspace guard. `workspace_id` / `user_id` are always derived here, never from the client.
- `app/core/rate_limit.py`, `app/core/audit.py`, `app/core/pagination.py` — cross-cutting concerns.
- `app/modules/auth`, `app/modules/workspace`, `app/modules/rbac`, `app/modules/shopify` —
  `models / schemas / service / router` per module; controllers hold no business logic.
  `shopify` implements Feature 2.1 OAuth (install, callback, status, disconnect),
  Feature 2.2 Initial Sync (manual sync, sync status, list orders/products/customers),
  Feature 2.3 Webhooks & Incremental Sync (webhook receive, incremental processing, webhook status),
  Milestone 3 Razorpay Integration (connect, disconnect, status, manual sync, list payments/refunds/settlements),
  Milestone 4 Financial Reconciliation Engine (run reconciliation, list results/exceptions, summary),
  Milestone 5 Dashboard & Analytics API (overview, revenue, orders, payments, refunds, settlements, exceptions, match rate, analytics),
  and Milestone 6 Production Readiness (export APIs, notification framework, health endpoints).
- `app/services/email.py` — templates, SMTP transport, and the `outbound_email` delivery ledger.

**Frontend (`frontend/src/`)**
- `lib/api.js` — versioned axios client, credentialed requests, silent refresh-and-retry (excluding
  the public auth endpoints), canonical error reader.
- `context/AuthContext.js` — session bootstrap from the refresh cookie, login/logout, workspace
  switching, `can(permission)` for permission-aware UI.
- `components/` — `AppShell` (sidebar, workspace switcher), `ProtectedRoute`, `AuthLayout`,
  `StateViews` (loading / empty / error).
- `pages/` — Landing, Login, Register, VerifyEmail, ForgotPassword, ResetPassword, AcceptInvitation,
  Dashboard, and `pages/settings/` (WorkspaceSettings, Members, Roles, Sessions).
- `constants/testIds/` — the `data-testid` registry used by automated e2e tests.

**Specifications (committed in-repo)** — `GANAKA_EMERGENT_CONTEXT_v4.md`, `docs/`, `implementation/`,
`AGENTS.md`.

## Verification state

- Backend: `python -m pytest tests/test_milestone1_auth_workspace.py -q` → **18 passed** (run from a
  clean rate-limiter state).
- Frontend: production build succeeds — `yarn build` exit 0, `153.6 kB` gzipped JS,
  `10.52 kB` gzipped CSS.
- Frontend e2e (platform testing agent, `test_reports/iteration_1.json`): 12/13 flows passed on the
  first pass; the one HIGH issue (failed login showing `AUTH-003` instead of `AUTH-001`) and two LOW
  issues were fixed and re-verified.
- QA account and operator commands: `memory/test_credentials.md`.

## Known limitations (carried forward)

1. No email transport configured — verification / reset / invitation links exist only in the
   `outbound_email` collection (status `PENDING_NO_TRANSPORT`).
2. Google sign-in returns `503 EXTERNAL-001` until `GOOGLE_CLIENT_ID` is set; its happy path is
   therefore unverified.
3. Google ID tokens are validated via Google's `tokeninfo` endpoint (network call) rather than local
   JWKS verification.
4. Rate limiting is a per-instance MongoDB fixed window, not a distributed bucket.
5. `ACCOUNTANT` has no "Reconciliation Read" permission because `DEFAULT_PERMISSIONS` defines no
   `reconciliation.read` code (spec gap, not invented).
6. MFA, magic-link login and multi-workspace *creation* UI are out of scope / undefined in the spec.
7. No metrics endpoint yet (belongs to Milestone 6).
8. Session absolute (30-day) and idle (30-minute) expiry are implemented but were not verified by
   waiting out real time.
9. Documentation vs. repository stack conflict is unresolved — see the note above.
