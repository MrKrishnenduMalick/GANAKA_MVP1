# Release Manifest — Ganaka MVP v1.0.0

## Project Name
Ganaka — Financial Reconciliation Platform

## Version
1.0.0 (2026-08) — see `VERSION.md` for history

## Repository Structure

```
GANAKA-main/
├── backend/                  FastAPI application
│   ├── app/
│   │   ├── core/              config, db, security, crypto, errors, deps, audit, rate_limit
│   │   ├── modules/
│   │   │   ├── auth/           authentication (register/login/sessions/password reset/Google)
│   │   │   ├── workspace/      workspaces, members, invitations, settings, RBAC-adjacent
│   │   │   ├── rbac/           roles and permissions
│   │   │   └── shopify/        Shopify + Razorpay + Reconciliation + Dashboard + Exports +
│   │   │                       Notifications + Health (see Known Limitations — this module
│   │   │                       intentionally was not split in this release)
│   │   └── services/           email (SMTP)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  React (CRA + CRACO) application
│   ├── src/
│   │   ├── pages/               20 top-level page files across auth, dashboard, shopify,
│   │   │                        razorpay, reconciliation, reports, notifications, settings
│   │   ├── components/          shared UI (shadcn/ui-based) + app shell
│   │   └── context/, lib/       auth context, API client
│   └── .env.example
├── docs/                     product/architecture/database/security specification (23 files)
├── implementation/           milestone-by-milestone implementation specs (14 files)
├── tests/                    backend test suite (8 files)
├── memory/                   original product requirements document
└── *.md                      20 top-level documentation files (this manifest included)
```

## Backend Stack

- **Language/runtime:** Python 3.11
- **Framework:** FastAPI 0.110.1
- **Database driver:** motor 3.3.1 (async MongoDB), no ORM/ODM
- **Validation:** Pydantic ≥2.6.4
- **Auth:** pyjwt ≥2.10.1 (HS256), bcrypt 4.1.3, passlib ≥1.7.4
- **HTTP client:** httpx ≥0.27.0 (Shopify/Razorpay API calls, added to `requirements.txt` in this
  release — was already in use but previously undeclared)
- **File generation:** openpyxl ≥3.1.0 (Excel), reportlab ≥4.0.0 (PDF) — both added to
  `requirements.txt` in this release for the export fix
- **Testing:** pytest ≥8.0.0, pytest-xdist

## Frontend Stack

- **Framework:** React 19
- **Build tooling:** Create React App + CRACO
- **Styling:** Tailwind CSS 3.4 + shadcn/ui components
- **Data/state:** @tanstack/react-query, React Context (auth)
- **Charts:** Recharts

## Database

- **Engine:** MongoDB 6.0+ (no server version pin in this repository; driver-compatible range)
- **Schema management:** no DDL — additive/idempotent index bootstrap via `db.bootstrap()`, run on
  application startup
- **Collections:** 31, including 2 added in this release (`export_file`, `notification_delivery_log`)
- **Named indexes:** 45, none duplicated (verified programmatically in Phase 6)
- **Multi-tenancy:** every tenant-owned collection is scoped by `workspace_id`; enforced at the
  query layer via `app/core/deps.py`, not left to individual endpoints to remember

## Third-Party Integrations

| Integration | Purpose | Status |
|---|---|---|
| Shopify | Order/product/customer import via OAuth + webhooks | Implementation Complete — requires real-world testing |
| Razorpay | Payment/refund/settlement import via per-workspace credentials + webhooks | Implementation Complete — corrected 2026-08, requires real-world testing |
| SMTP | Transactional email (auth flows + notifications) | Implementation Complete — requires real SMTP server to verify delivery |
| Generic webhooks | Outbound notification delivery to a workspace-configured URL | Implementation Complete — requires a real receiving endpoint to verify delivery |
| Google OAuth | Sign-in | Implementation Complete — requires `GOOGLE_CLIENT_ID` configured |

## Environment Variables

Full, corrected lists in `backend/.env.example` and `frontend/.env.example` (both verified against
actual source-code usage in Phase 6 — every variable `config.py`/the frontend source reads is now
documented, and no documented variable is unused). Summary:

- **Backend, required:** `MONGO_URL`, `DB_NAME`, `JWT_SECRET`
- **Backend, optional integrations:** `SHOPIFY_API_KEY`/`SHOPIFY_API_SECRET` (or
  `SHOPIFY_CLIENT_ID`/`SHOPIFY_CLIENT_SECRET`), `GOOGLE_CLIENT_ID`, SMTP settings
- **Backend, corrected 2026-08:** no deployment-level Razorpay credential exists any more (was
  `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`/`RAZORPAY_WEBHOOK_SECRET`, now per-workspace via the app)
- **Backend, new 2026-08:** `ENVIRONMENT`, `ENABLE_TEST_ENDPOINTS`
- **Frontend:** `REACT_APP_BACKEND_URL` (required), `WDS_SOCKET_PORT`, `ENABLE_HEALTH_CHECK`
  (dev-only)

## API Route Count

81 routes across 4 router modules (`auth`, `workspace`, `rbac`, and the combined
`shopify`/`razorpay`/`reconciliation`/`dashboard`/`exports`/`notifications`/`health` module).
Verified in Phase 6: all routers are mounted in `server.py`, zero duplicate method+path
combinations across the entire backend.

## Frontend Page Count

20 top-level page files under `frontend/src/pages/`, spanning authentication, dashboard, Shopify
integration, Razorpay integration, reconciliation, reports, notifications, and settings. All
frontend `api.*()` call paths were verified in Phase 6 against the actual registered backend
routes — zero broken references found.

## Documentation Files

- 22 top-level Markdown files (including this manifest and the other Phase 7/8/9 artifacts)
- 23 files under `docs/`
- 14 files under `implementation/`
- **Total: 59 documentation files**

## Known Limitations

Full detail in `FINAL_RELEASE_REPORT.md` § Known Limitations. Summary:

1. Backend module boundary ("god module") — deferred, not fixed, by explicit scope decision
2. Settlement matching is an improved heuristic, not a fully precise match
3. Shopify webhook spoofing mitigation is partial (order-topic payloads only)
4. `shopify_connection` has the same reconnect-after-disconnect index bug found and fixed for
   `razorpay_connection`, left unfixed as out of scope
5. `client_ip()` trusts `X-Forwarded-For` unconditionally
6. No idempotency guard on manual Razorpay sync
7. Missing TTL indexes on several short-lived token collections
8. `money_at_risk` is computed correctly by the backend but not yet rendered in the frontend
   dashboard (discovered in Phase 6 of this release)

## Manual Testing Required

None of the following were reachable in the sandbox this release was prepared in (no network
egress). Full checklist with sub-items in `FIX_SUMMARY.md` § Manual Testing Required:

- Live Shopify OAuth install/callback, webhook delivery, full/incremental sync
- Live Razorpay credential verification, webhook delivery, sync, reconnect-after-disconnect
- Live SMTP email delivery and outbound webhook delivery
- Opening real generated CSV/Excel/PDF exports in their respective applications
- `pip install -r requirements.txt`, `db.bootstrap()` against a live MongoDB, `yarn build`, any
  pytest suite, CORS behavior with a real `APP_BASE_URL`

## Deployment Targets

Per `DEPLOYMENT.md`: backend on Render (or any ASGI-compatible host), frontend on Vercel (or any
static-hosting platform that can serve a CRA build). MongoDB via Atlas or self-hosted. No
container/orchestration platform (Docker/Kubernetes) is provided or required by this repository —
consistent with the product's explicit MVP scope, which names Kubernetes and microservices as
out-of-scope.
