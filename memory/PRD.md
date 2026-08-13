# Ganaka — PRD / Working Memory

## Original problem statement
Continue the Ganaka MVP from the uploaded repository. Detect the technology stack from the repository
itself (never from the context docs or platform defaults) and use only that stack — no framework, DB,
ORM, auth-library, API-architecture or build-system changes. Determine the next incomplete milestone,
diff its Definition of Done against the actual implementation, implement only the Missing and
Incorrect items, preserve architecture / API contracts / auth model / workspace isolation / schema
(additive + idempotent migrations only), keep imported financial records immutable, enforce
server-side authorization and workspace isolation on all new code with `workspace_id`/`user_id`
derived from the session, verify honestly, then update `IMPLEMENTATION_REPORT.md`,
`PROJECT_STATUS.md`, `FILES_CHANGED.md`, `NEXT_MILESTONE.md` and stop.

## User choices (2026-06 session)
- Fill only the gaps (Missing / Incorrect). Do not rebuild completed work.
- User will supply integration keys when asked (none supplied yet).
- Testing depth: backend + frontend end-to-end.
- Strictly follow `NEXT_MILESTONE.md`; no scope expansion, no future milestones, no architecture
  redesign, no new frameworks. On a blocker: stop, document in `IMPLEMENTATION_REPORT.md`, wait.

## Product
Financial reconciliation SaaS for Indian Shopify-based D2C brands. Imports Shopify orders and
Razorpay payments/refunds/settlements, reconciles with deterministic rules, and surfaces auditable
evidence (ghost orders, missing payments, duplicate payments, amount mismatch, refund mismatch,
settlement difference, money at risk). Principles: Correctness > Transparency > Auditability >
Reliability. Users: non-technical finance/ops staff and their accountants.
Success criteria: a merchant can Register → Login → Connect Shopify → Connect Razorpay → Import →
Reconcile → View dashboard → Understand every discrepancy → Download reports, without developer help.

## Detected technology stack (from repo inspection — authoritative)
FastAPI 0.110 / Python 3.11 · MongoDB via motor 3.3, no ORM/ODM · Pydantic v2 · custom JWT
(pyjwt HS256 + bcrypt) · REST at `/api/v1` · React 19 + CRA/CRACO (JavaScript) · Tailwind 3.4 +
shadcn/ui · yarn · pytest · no background-job framework · no active third-party integrations.

**Open Critical conflict:** the specification documents (`README`, `docs/03`, `docs/04` DB-001,
`implementation/00_FOUNDATION`) specify Next.js 15 + Spring Boot 3 / Java 21 + PostgreSQL + Redis +
Flyway and explicitly forbid MongoDB. The uploaded Ganaka repository contained specifications only
(41 files, zero source files), so there was no such implementation to preserve; the working
repository's real, running stack was used and the conflict is documented in
`IMPLEMENTATION_REPORT.md`. Product owner must resolve before Milestone 2.

## Milestones
1. Authentication & Workspace — ✅ **complete (2026-06)**
2. Shopify Integration — next
3. Razorpay Integration
4. Financial Reconciliation Engine
5. Dashboard, Reports & Audit Center
6. Production Readiness & Beta Release

## What's been implemented
**2026-06 — Milestone 1 (Authentication & Workspace)**
- Backend: modular `backend/app/{core,modules,services}`; email/password auth with enumeration
  protection, email verification, password reset, Google sign-in endpoint, JWT 15m + rotating 30d
  refresh token in an httpOnly/Secure/SameSite=Strict cookie scoped to the refresh path, sessions
  (max 5, 30m idle, revocation), account lockout (5 failures → 15m), password policy, per-endpoint
  rate limits, canonical error envelope + request ids, append-only audit log, idempotent
  index/seed bootstrap, workspaces + settings (incl. reconciliation tolerances), 5 default roles,
  16-permission RBAC resolved server-side, invitations, workspace switch, ownership transfer, and
  tenant isolation on every query.
- Frontend: landing, register (live password checklist), login, verify email, forgot/reset password,
  accept invitation, app shell with workspace switcher, dashboard with a truthful empty state,
  workspace settings, members + invite, roles matrix, active sessions.
- Verification: 18/18 backend integration tests pass; frontend production build succeeds; frontend
  e2e 12/13 first pass, then the 1 HIGH + 2 LOW findings fixed and re-verified.
- Not verified (documented): Google sign-in happy path (no `GOOGLE_CLIENT_ID`), real email delivery
  (no SMTP — emails land in the `outbound_email` ledger), long-duration session expiry.

## Prioritized backlog
**P0 — before Milestone 2 can start**
- Resolve the documentation-vs-repository stack conflict.
- Decide the async webhook processing approach (Mongo-backed worker vs. Celery/Redis).
- Obtain Shopify Partner credentials + development store, and an AES-256 `ENCRYPTION_KEY`.

**P1 — Milestone 2 (Shopify Integration)**
- OAuth connect/callback with `*.myshopify.com` allowlist + SSRF protection, AES-256 token storage,
  store verification, webhook registration, initial/incremental/manual sync with cursor + idempotent
  dedupe, retry (5 attempts, exponential backoff, DLQ), disconnect/reconnect, HMAC-verified webhook
  endpoint, the three mandatory compliance webhooks, and full auditing.

**P2 — later milestones**
- Razorpay import (M3); reconciliation engine consuming the stored tolerances (M4); dashboard,
  reports and audit center (M5); metrics, monitoring, email provider, Google credentials and
  distributed rate limiting (M6).
